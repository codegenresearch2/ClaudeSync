import os
import hashlib
from functools import wraps
import click
import pathspec
import logging
import urllib.request
import gzip
from claudesync.exceptions import ConfigurationError, ProviderError
from claudesync.provider_factory import get_provider
from claudesync.config_manager import ConfigManager

logger = logging.getLogger(__name__)
config_manager = ConfigManager()

# Define constants
SAMPLE_SIZE = 8192

def normalize_and_calculate_md5(content):
    """
    Normalize line endings, strip whitespace, and calculate the MD5 checksum of the given content.

    Args:
        content (str): The content for which to calculate the checksum.

    Returns:
        str: The hexadecimal MD5 checksum of the normalized content.
    """
    normalized_content = content.replace("\r\n", "\n").replace("\r", "\n").strip()
    return hashlib.md5(normalized_content.encode("utf-8")).hexdigest()

def load_gitignore(base_path):
    """
    Load and parse the .gitignore file from the specified base path.

    Args:
        base_path (str): The base directory path where the .gitignore file is located.

    Returns:
        pathspec.PathSpec or None: A PathSpec object containing the patterns from the .gitignore file
                                    if the file exists; otherwise, None.
    """
    gitignore_path = os.path.join(base_path, ".gitignore")
    if os.path.exists(gitignore_path):
        with open(gitignore_path, "r") as f:
            return pathspec.PathSpec.from_lines("gitwildmatch", f)
    return None

def is_text_file(file_path, sample_size=SAMPLE_SIZE):
    """
    Determine if a file is a text file by checking for the absence of null bytes.

    Args:
        file_path (str): The path to the file to be checked.
        sample_size (int, optional): The number of bytes to read from the file for checking.
                                     Defaults to the value of SAMPLE_SIZE.

    Returns:
        bool: True if the file is likely a text file, False if it is likely binary or an error occurred.
    """
    try:
        with open(file_path, "rb") as file:
            return b"\x00" not in file.read(sample_size)
    except IOError:
        return False

def compute_md5_hash(content):
    """
    Compute the MD5 hash of the given content.

    Args:
        content (str): The content for which to compute the MD5 hash.

    Returns:
        str: The hexadecimal MD5 hash of the input content.
    """
    return hashlib.md5(content.encode("utf-8")).hexdigest()

def should_process_file(file_path, filename, gitignore, base_path, claudeignore):
    """
    Determine whether a file should be processed based on various criteria.

    Args:
        file_path (str): The full path to the file.
        filename (str): The name of the file.
        gitignore (pathspec.PathSpec or None): A PathSpec object containing .gitignore patterns, if available.
        base_path (str): The base directory path of the project.
        claudeignore (pathspec.PathSpec or None): A PathSpec object containing .claudeignore patterns, if available.

    Returns:
        bool: True if the file should be processed, False otherwise.
    """
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
    """
    Read the content of a file and compute its MD5 hash.

    Args:
        file_path (str): The path to the file to be processed.

    Returns:
        str or None: The MD5 hash of the file's content if successful, None otherwise.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()
            return compute_md5_hash(content)
    except UnicodeDecodeError:
        logger.debug(f"Unable to read {file_path} as UTF-8 text. Skipping.")
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {str(e)}")
    return None

def get_local_files(local_path):
    """
    Retrieve a dictionary of local files within a specified path, applying various filters.

    Args:
        local_path (str): The base directory path to search for files.

    Returns:
        dict: A dictionary where keys are relative file paths, and values are MD5 hashes of the file contents.
    """
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
            if should_process_file(
                full_path, filename, gitignore, local_path, claudeignore
            ):
                file_hash = process_file(full_path)
                if file_hash:
                    files[rel_path] = file_hash
    return files

def handle_errors(func):
    """
    A decorator that wraps a function to catch and handle specific exceptions.

    Args:
        func (Callable): The function to be decorated.

    Returns:
        Callable: The wrapper function that includes exception handling.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (ConfigurationError, ProviderError) as e:
            click.echo(f"Error: {str(e)}")
    return wrapper

def validate_and_get_provider(config, require_org=True, require_project=False):
    """
    Validate the configuration for the presence of an active provider and session key,
    and optionally checks for an active organization ID and project ID. If validation passes,
    retrieve the provider instance based on the active provider name.

    Args:
        config (ConfigManager): The configuration manager instance containing settings.
        require_org (bool, optional): Flag to indicate whether an active organization ID
                                      is required. Defaults to True.
        require_project (bool, optional): Flag to indicate whether an active project ID
                                          is required. Defaults to False.

    Returns:
        object: An instance of the provider specified in the configuration.

    Raises:
        ConfigurationError: If the active provider or session key is missing, or if
                            require_org is True and no active organization ID is set,
                            or if require_project is True and no active project ID is set.
        ProviderError: If the session key has expired.
    """
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
    """
    Prompt the user for the absolute path to their local project directory and store it in the configuration.

    Args:
        config (ConfigManager): The configuration manager instance to store the local path setting.
    """
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
    """
    Load and parse the .claudeignore file from the specified base path.

    Args:
        base_path (str): The base directory path where the .claudeignore file is located.

    Returns:
        pathspec.PathSpec or None: A PathSpec object containing the patterns from the .claudeignore file
                                    if the file exists; otherwise, None.
    """
    claudeignore_path = os.path.join(base_path, ".claudeignore")
    if os.path.exists(claudeignore_path):
        with open(claudeignore_path, "r") as f:
            return pathspec.PathSpec.from_lines("gitwildmatch", f)
    return None

def handle_http_errors(func):
    """
    A decorator that wraps a function to handle HTTP errors and decompress gzip responses.

    Args:
        func (Callable): The function to be decorated.

    Returns:
        Callable: The wrapper function that includes HTTP error handling and gzip decompression.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            req = urllib.request.Request(kwargs["url"])
            req.add_header("Accept-Encoding", "gzip")
            response = urllib.request.urlopen(req)
            if response.info().get("Content-Encoding") == "gzip":
                content = gzip.decompress(response.read())
            else:
                content = response.read()
            return func(content, *args, **kwargs)
        except urllib.error.HTTPError as e:
            click.echo(f"HTTP Error {e.code}: {e.reason}")
        except urllib.error.URLError as e:
            click.echo(f"URL Error: {e.reason}")
    return wrapper

I have addressed the feedback from the oracle by adding docstrings to each function, providing more context in function names and descriptions, organizing the code structure, ensuring consistency in style, and defining constants for magic numbers. I have also removed the extraneous comment that was causing the syntax error in the tests.