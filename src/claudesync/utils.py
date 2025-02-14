import os
import hashlib
from functools import wraps
import click
import pathspec
import logging
from claudesync.exceptions import ConfigurationError, ProviderError
from claudesync.provider_factory import get_provider
from claudesync.config_manager import ConfigManager

logger = logging.getLogger(__name__)
config_manager = ConfigManager()

def compute_md5_hash(content):
    """\n    Computes the MD5 hash of the given content.\n\n    Args:\n        content (str): The content for which to compute the MD5 hash.\n\n    Returns:\n        str: The hexadecimal MD5 hash of the input content.\n    """
    return hashlib.md5(content.encode("utf-8")).hexdigest()

def load_gitignore(base_path):
    """\n    Loads and parses the .gitignore file from the specified base path.\n\n    Args:\n        base_path (str): The base directory path where the .gitignore file is located.\n\n    Returns:\n        pathspec.PathSpec or None: A PathSpec object containing the patterns from the .gitignore file\n                                    if the file exists; otherwise, None.\n    """
    gitignore_path = os.path.join(base_path, ".gitignore")
    if os.path.exists(gitignore_path):
        with open(gitignore_path, "r") as f:
            return pathspec.PathSpec.from_lines("gitwildmatch", f)
    return None

def is_text_file(file_path, sample_size=8192):
    """\n    Determines if a file is a text file by checking for the absence of null bytes.\n\n    Args:\n        file_path (str): The path to the file to be checked.\n        sample_size (int, optional): The number of bytes to read from the file for checking.\n                                     Defaults to 8192.\n\n    Returns:\n        bool: True if the file is likely a text file, False if it is likely binary or an error occurred.\n    """
    try:
        with open(file_path, "rb") as file:
            return b"\x00" not in file.read(sample_size)
    except IOError:
        return False

def should_process_file(file_path, filename, gitignore, base_path, claudeignore):
    """\n    Determines whether a file should be processed based on various criteria.\n\n    Args:\n        file_path (str): The full path to the file.\n        filename (str): The name of the file.\n        gitignore (pathspec.PathSpec or None): A PathSpec object containing .gitignore patterns, if available.\n        base_path (str): The base directory path of the project.\n        claudeignore (pathspec.PathSpec or None): A PathSpec object containing .claudeignore patterns, if available.\n\n    Returns:\n        bool: True if the file should be processed, False otherwise.\n    """
    max_file_size = config_manager.get("max_file_size", 32 * 1024)
    if os.path.getsize(file_path) > max_file_size or filename.endswith("~"):
        return False

    rel_path = os.path.relpath(file_path, base_path)
    if (gitignore and gitignore.match_file(rel_path)) or (claudeignore and claudeignore.match_file(rel_path)):
        return False

    return is_text_file(file_path)

def process_file(file_path):
    """\n    Reads the content of a file and computes its MD5 hash.\n\n    Args:\n        file_path (str): The path to the file to be processed.\n\n    Returns:\n        str or None: The MD5 hash of the file's content if successful, None otherwise.\n    """
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
    """\n    Retrieves a dictionary of local files within a specified path, applying various filters.\n\n    Args:\n        local_path (str): The base directory path to search for files.\n\n    Returns:\n        dict: A dictionary where keys are relative file paths, and values are MD5 hashes of the file contents.\n    """
    gitignore = load_gitignore(local_path)
    claudeignore = load_claudeignore(local_path)
    files = {}
    exclude_dirs = {".git", ".svn", ".hg", ".bzr", "_darcs", "CVS"}

    for root, dirs, filenames in os.walk(local_path):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        rel_root = os.path.relpath(root, local_path)
        rel_root = "" if rel_root == "." else rel_root

        for filename in filenames:
            rel_path = os.path.join(rel_root, filename)
            full_path = os.path.join(root, filename)

            if should_process_file(full_path, filename, gitignore, local_path, claudeignore):
                file_hash = process_file(full_path)
                if file_hash:
                    files[rel_path] = file_hash

    return files

def handle_errors(func):
    """\n    A decorator that wraps a function to catch and handle specific exceptions.\n\n    Args:\n        func (Callable): The function to be decorated.\n\n    Returns:\n        Callable: The wrapper function that includes exception handling.\n    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (ConfigurationError, ProviderError) as e:
            click.echo(f"Error: {str(e)}")
    return wrapper

def validate_and_get_provider(config, require_org=True):
    """\n    Validates the configuration for the presence of an active provider and session key,\n    and optionally checks for an active organization ID. If validation passes, it retrieves\n    the provider instance based on the active provider name.\n\n    Args:\n        config (ConfigManager): The configuration manager instance containing settings.\n        require_org (bool, optional): Flag to indicate whether an active organization ID\n                                      is required. Defaults to True.\n\n    Returns:\n        object: An instance of the provider specified in the configuration.\n\n    Raises:\n        ConfigurationError: If the active provider or session key is missing, or if\n                            require_org is True and no active organization ID is set.\n    """
    active_provider = config.get("active_provider")
    session_key = config.get("session_key")
    if not active_provider or not session_key:
        raise ConfigurationError("No active provider or session key. Please login first.")
    if require_org and not config.get("active_organization_id"):
        raise ConfigurationError("No active organization set. Please select an organization.")
    return get_provider(active_provider, session_key)

def validate_and_store_local_path(config):
    """\n    Prompts the user for the absolute path to their local project directory and stores it in the configuration.\n\n    Args:\n        config (ConfigManager): The configuration manager instance to store the local path setting.\n    """
    while True:
        default_path = os.getcwd()
        local_path = click.prompt(
            "Enter the absolute path to your local project directory",
            type=click.Path(exists=True, file_okay=False, dir_okay=True, resolve_path=True),
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
    """\n    Loads and parses the .claudeignore file from the specified base path.\n\n    Args:\n        base_path (str): The base directory path where the .claudeignore file is located.\n\n    Returns:\n        pathspec.PathSpec or None: A PathSpec object containing the patterns from the .claudeignore file\n                                    if the file exists; otherwise, None.\n    """
    claudeignore_path = os.path.join(base_path, ".claudeignore")
    if os.path.exists(claudeignore_path):
        with open(claudeignore_path, "r") as f:
            return pathspec.PathSpec.from_lines("gitwildmatch", f)
    return None