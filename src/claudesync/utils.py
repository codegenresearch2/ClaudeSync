import os
import hashlib
from functools import wraps
import urllib.request
import gzip
import io
import click
import pathspec
import logging
from claudesync.exceptions import ConfigurationError, ProviderError
from claudesync.provider_factory import get_provider
from claudesync.config_manager import ConfigManager

logger = logging.getLogger(__name__)
config_manager = ConfigManager()


def normalize_and_calculate_md5(content):
    normalized_content = content.replace("\r\n", "\n").replace("\r", "\n").strip()
    return hashlib.md5(normalized_content.encode("utf-8")).hexdigest()


def load_gitignore(base_path):
    gitignore_path = os.path.join(base_path, ".gitignore")
    if os.path.exists(gitignore_path):
        with open(gitignore_path, "r") as f:
            return pathspec.PathSpec.from_lines("gitwildmatch", f)
    return None


def is_text_file(file_path, sample_size=8192):
    try:
        with urllib.request.urlopen(file_path) as response:
            if "content-encoding" in response.headers and response.headers["content-encoding"] == "gzip":
                buffer = io.BytesIO(response.read())
                with gzip.GzipFile(fileobj=buffer) as gzipped_file:
                    return b"\x00" not in gzipped_file.read(sample_size)
            else:
                return b"\x00" not in response.read(sample_size)
    except Exception:
        return False


def compute_md5_hash(content):
    return hashlib.md5(content.encode("utf-8")).hexdigest()


def should_process_file(file_path, filename, gitignore, base_path, claudeignore):
    max_file_size = config_manager.get("max_file_size", 32 * 1024)
    if os.path.getsize(file_path) > max_file_size:
        return False
    if filename.endswith("~"):
        return False
    rel_path = os.path.relpath(file_path, base_path)
    if gitignore and gitignore.match_file(rel_path):
        return False
    if claudeignore and claudeignore.match_file(rel_path):
        return False
    return is_text_file(file_path)


def process_file(file_path):
    try:
        with urllib.request.urlopen(file_path) as response:
            if "content-encoding" in response.headers and response.headers["content-encoding"] == "gzip":
                buffer = io.BytesIO(response.read())
                with gzip.GzipFile(fileobj=buffer) as gzipped_file:
                    content = gzipped_file.read().decode("utf-8")
            else:
                content = response.read().decode("utf-8")
            return compute_md5_hash(content)
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {str(e)}")
    return None


def get_local_files(local_path):
    gitignore = load_gitignore(local_path)
    claudeignore = load_claudeignore(local_path)
    files = {}
    exclude_dirs = {".git", ".svn", ".hg", ".bzr", "_darcs", "CVS", "claude_chats"}

    for root, dirs, filenames in os.walk(local_path, topdown=True):
        rel_root = os.path.relpath(root, local_path)
        rel_root = "" if rel_root == "." else rel_root
        dirs[:] = [
            d for d in dirs
            if d not in exclude_dirs
            and not (gitignore and gitignore.match_file(os.path.join(rel_root, d)))
            and not (claudeignore and claudeignore.match_file(os.path.join(rel_root, d)))
        ]
        for filename in filenames:
            rel_path = os.path.join(rel_root, filename)
            full_path = os.path.join(root, filename)
            if should_process_file(full_path, filename, gitignore, local_path, claudeignore):
                file_hash = process_file(full_path)
                if file_hash:
                    files[rel_path] = file_hash
    return files


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
        raise ProviderError(
            f"Session key has expired. Please run `claudesync api login {active_provider}` again."
        )
    if not active_provider or not session_key:
        raise ConfigurationError(
            "No active provider or session key. Please login first."
        )
    if require_org and not config.get("active_organization_id"):
        raise ConfigurationError(
            "No active organization set. Please select an organization."
        )
    if require_project and not config.get("active_project_id"):
        raise ConfigurationError(
            "No active project set. Please select or create a project."
        )
    session_key_expiry = config.get("session_key_expiry")
    return get_provider(active_provider, session_key, session_key_expiry)


def validate_and_store_local_path(config):
    def get_default_path():
        return os.getcwd()

    while True:
        default_path = get_default_path()
        local_path = click.prompt(
            "Enter the absolute path to your local project directory",
            type=click.Path(
                exists=True, file_okay=False, dir_okay=True, resolve_path=True
            ),
            default=default_path,
            show_default=True,
        )
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