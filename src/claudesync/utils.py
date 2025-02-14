import os
import hashlib
from functools import wraps
import click
import pathspec
import logging
import gzip
import urllib.request
from urllib.error import URLError, HTTPError
from claudesync.exceptions import ConfigurationError, ProviderError
from claudesync.provider_factory import get_provider
from claudesync.config_manager import ConfigManager

logger = logging.getLogger(__name__)
config_manager = ConfigManager()

# ... (other functions remain the same)

def compute_md5_hash(content):
    return hashlib.md5(content.encode("utf-8")).hexdigest()

def process_file(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()
            return compute_md5_hash(content)
    except UnicodeDecodeError:
        logger.debug(f"Unable to read {file_path} as UTF-8 text. Skipping.")
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {str(e)}")
    return None

def handle_errors(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (ConfigurationError, ProviderError) as e:
            click.echo(f"Error: {str(e)}")

    return wrapper

def validate_and_get_provider(config, require_org=True, require_project=False):
    active_provider = config.get("active_provider")
    session_key = config.get_session_key()
    if not session_key:
        raise ProviderError(f"Session key has expired. Please run `claudesync api login {active_provider}` again.")
    if not active_provider or not session_key:
        raise ConfigurationError("No active provider or session key. Please login first.")
    if require_org and not config.get("active_organization_id"):
        raise ConfigurationError("No active organization set. Please select an organization.")
    if require_project and not config.get("active_project_id"):
        raise ConfigurationError("No active project set. Please select or create a project.")
    session_key_expiry = config.get("session_key_expiry")
    return get_provider(active_provider, session_key, session_key_expiry)

def validate_and_store_local_path(config):
    def get_default_path():
        return os.getcwd()

    while True:
        default_path = get_default_path()
        local_path = click.prompt("Enter the absolute path to your local project directory", type=click.Path(exists=True, file_okay=False, dir_okay=True, resolve_path=True), default=default_path, show_default=True)

        if os.path.isabs(local_path):
            config.set("local_path", local_path)
            click.echo(f"Local path set to: {local_path}")
            break
        else:
            click.echo("Please enter an absolute path.")

def load_claudeignore(base_path):
    claudeignore_path = os.path.join(base_path, ".claudeignore")
    if os.path.exists(claudeignore_path):
        with open(claudeignore_path, "r") as f:
            return pathspec.PathSpec.from_lines("gitwildmatch", f)
    return None

def handle_http_errors(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except HTTPError as e:
            click.echo(f"HTTP Error {e.code}: {e.reason}")
        except URLError as e:
            click.echo(f"URL Error: {e.reason}")
        except Exception as e:
            click.echo(f"An error occurred: {str(e)}")

    return wrapper

@handle_http_errors
def make_http_request(url, headers=None, data=None, method="GET"):
    req = urllib.request.Request(url, headers=headers, data=data, method=method)
    with urllib.request.urlopen(req) as response:
        content_encoding = response.info().get("Content-Encoding")
        if content_encoding == "gzip":
            return gzip.decompress(response.read())
        else:
            return response.read()