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


def normalize_and_calculate_md5(content):
    """\n    Calculate the MD5 checksum of the given content after normalizing line endings.\n\n    This function normalizes the line endings of the input content to Unix-style (\n),\n    strips leading and trailing whitespace, and then calculates the MD5 checksum of the\n    normalized content. This is useful for ensuring consistent checksums across different\n    operating systems and environments where line ending styles may vary.\n\n    Args:\n        content (str): The content for which to calculate the checksum.\n\n    Returns:\n        str: The hexadecimal MD5 checksum of the normalized content.\n    """
    normalized_content = content.replace("\r\n", "\n").replace("\r", "\n").strip()
    return hashlib.md5(normalized_content.encode("utf-8")).hexdigest()


def load_gitignore(base_path):
    """\n    Loads and parses the .gitignore file from the specified base path.\n\n    This function attempts to find a .gitignore file in the given base path. If found,\n    it reads the file and creates a PathSpec object that can be used to match paths\n    against the patterns defined in the .gitignore file. This is useful for filtering\n    out files that should be ignored based on the project's .gitignore settings.\n\n    Args:\n        base_path (str): The base directory path where the .gitignore file is located.\n\n    Returns:\n        pathspec.PathSpec or None: A PathSpec object containing the patterns from the .gitignore file\n                                    if the file exists; otherwise, None.\n    """
    gitignore_path = os.path.join(base_path, ".gitignore")
    if os.path.exists(gitignore_path):
        with open(gitignore_path, "r") as f:
            return pathspec.PathSpec.from_lines("gitwildmatch", f)
    return None


def is_text_file(file_path, sample_size=8192):
    """\n    Determines if a file is a text file by checking for the absence of null bytes.\n\n    This function reads a sample of the file (default 8192 bytes) and checks if it contains\n    any null byte (\x00). The presence of a null byte is often indicative of a binary file.\n    This is a heuristic method and may not be 100% accurate for all file types.\n\n    Args:\n        file_path (str): The path to the file to be checked.\n        sample_size (int, optional): The number of bytes to read from the file for checking.\n                                     Defaults to 8192.\n\n    Returns:\n        bool: True if the file is likely a text file, False if it is likely binary or an error occurred.\n    """
    try:
        with open(file_path, "rb") as file:
            return b"\x00" not in file.read(sample_size)
    except IOError:
        return False


def compute_md5_hash(content):
    """\n    Computes the MD5 hash of the given content.\n\n    This function takes a string as input, encodes it into UTF-8, and then computes the MD5 hash of the encoded string.\n    The result is a hexadecimal representation of the hash, which is commonly used for creating a quick and simple\n    fingerprint of a piece of data.\n\n    Args:\n        content (str): The content for which to compute the MD5 hash.\n\n    Returns:\n        str: The hexadecimal MD5 hash of the input content.\n    """
    return hashlib.md5(content.encode("utf-8")).hexdigest()


def should_process_file(file_path, filename, gitignore, base_path, claudeignore):
    """\n    Determines whether a file should be processed based on various criteria.\n\n    This function checks if a file should be included in the synchronization process by applying\n    several filters:\n    - Checks if the file size is within the configured maximum limit.\n    - Skips temporary editor files (ending with '~').\n    - Applies .gitignore rules if a gitignore PathSpec is provided.\n    - Verifies if the file is a text file.\n\n    Args:\n        file_path (str): The full path to the file.\n        filename (str): The name of the file.\n        gitignore (pathspec.PathSpec or None): A PathSpec object containing .gitignore patterns, if available.\n        base_path (str): The base directory path of the project.\n        claudeignore (pathspec.PathSpec or None): A PathSpec object containing .claudeignore patterns, if available.\n\n    Returns:\n        bool: True if the file should be processed, False otherwise.\n    """
    # Check file size
    max_file_size = config_manager.get("max_file_size", 32 * 1024)
    if os.path.getsize(file_path) > max_file_size:
        return False

    # Skip temporary editor files
    if filename.endswith("~"):
        return False

    rel_path = os.path.relpath(file_path, base_path)

    # Use gitignore rules if available
    if gitignore and gitignore.match_file(rel_path):
        return False

    # Use .claudeignore rules if available
    if claudeignore and claudeignore.match_file(rel_path):
        return False

    # Check if it's a text file\n    return is_text_file(file_path)\n\n\ndef process_file(file_path):\n    """\n    Reads the content of a file and computes its MD5 hash.\n\n    This function attempts to read the file as UTF-8 text and compute its MD5 hash.\n    If the file cannot be read as UTF-8 or any other error occurs, it logs the issue\n    and returns None.\n\n    Args:\n        file_path (str): The path to the file to be processed.\n\n    Returns:\n        str or None: The MD5 hash of the file's content if successful, None otherwise.
    """\n    try:\n        with open(file_path, "r", encoding="utf-8") as file:\n            content = file.read()\n            return compute_md5_hash(content)\n    except UnicodeDecodeError:\n        logger.debug(f"Unable to read {file_path} as UTF-8 text. Skipping.")\n    except Exception as e:\n        logger.error(f"Error reading file {file_path}: {str(e)}")\n    return None\n\n\ndef get_local_files(local_path):\n    """
    Retrieves a dictionary of local files within a specified path, applying various filters.

    This function walks through the directory specified by `local_path`, applying several filters to each file:
    - Excludes files in directories like .git, .svn, etc.
    - Skips files larger than a specified maximum size (default 200KB, configurable).
    - Ignores temporary editor files (ending with '~').
    - Applies .gitignore rules if a .gitignore file is present in the `local_path`.
    - Applies .gitignore rules if a .claudeignore file is present in the `local_path`.
    - Checks if the file is a text file before processing.
    Each file that passes these filters is read, and its content is hashed using MD5. The function returns a dictionary
    where each key is the relative path of a file from `local_path`, and its value is the MD5 hash of the file's content.\n\n    Args:\n        local_path (str): The base directory path to search for files.\n\n    Returns:\n        dict: A dictionary where keys are relative file paths, and values are MD5 hashes of the file contents.\n    """\n    gitignore = load_gitignore(local_path)\n    claudeignore = load_claudeignore(local_path)\n    files = {}\n    exclude_dirs = {".git", ".svn", ".hg", ".bzr", "_darcs", "CVS"}\n\n    for root, dirs, filenames in os.walk(local_path):\n        dirs[:] = [d for d in dirs if d not in exclude_dirs]\n        rel_root = os.path.relpath(root, local_path)\n        rel_root = "" if rel_root == "." else rel_root\n\n        for filename in filenames:\n            rel_path = os.path.join(rel_root, filename)\n            full_path = os.path.join(root, filename)\n\n            if should_process_file(\n                full_path, filename, gitignore, local_path, claudeignore\n            ):\n                file_hash = process_file(full_path)\n                if file_hash:\n                    files[rel_path] = file_hash\n\n    return files\n\n\ndef handle_errors(func):\n    """\n    A decorator that wraps a function to catch and handle specific exceptions.\n\n    This decorator catches exceptions of type ConfigurationError and ProviderError\n    that are raised within the decorated function. When such an exception is caught,\n    it prints an error message to the console using click's echo function. This is
    useful for CLI applications where a friendly error message is preferred over a
    full traceback for known error conditions.

    Args:
        func (Callable): The function to be decorated.

    Returns:
        Callable: The wrapper function that includes exception handling.
    """\n\n    @wraps(func)\n    def wrapper(*args, **kwargs):\n        try:\n            return func(*args, **kwargs)\n        except (ConfigurationError, ProviderError) as e:\n            click.echo(f"Error: {str(e)}")\n\n    return wrapper\n\n\ndef validate_and_get_provider(config, require_org=True):\n    """
    Validates the configuration for the presence of an active provider and session key,
    and optionally checks for an active organization ID. If validation passes, it retrieves
    the provider instance based on the active provider name.

    This function ensures that the necessary configuration settings are present before
    attempting to interact with a provider. It raises a ConfigurationError if the required
    settings are missing, guiding the user to perform necessary setup steps.

    Args:
        config (ConfigManager): The configuration manager instance containing settings.
        require_org (bool, optional): Flag to indicate whether an active organization ID
                                      is required. Defaults to True.

    Returns:
        object: An instance of the provider specified in the configuration.

    Raises:
        ConfigurationError: If the active provider or session key is missing, or if
                            require_org is True and no active organization ID is set.
    """\n    active_provider = config.get("active_provider")\n    session_key = config.get("session_key")\n    if not active_provider or not session_key:\n        raise ConfigurationError(\n            "No active provider or session key. Please login first."\n        )\n    if require_org and not config.get("active_organization_id"):\n        raise ConfigurationError(\n            "No active organization set. Please select an organization."\n        )\n    return get_provider(active_provider, session_key)\n\n\ndef validate_and_store_local_path(config):\n    """
    Prompts the user for the absolute path to their local project directory and stores it in the configuration.

    This function repeatedly prompts the user to enter the absolute path to their local project directory until
    a valid absolute path is provided. The path is validated to ensure it exists, is a directory, and is an absolute path.
    Once a valid path is provided, it is stored in the configuration using the `set` method of the `ConfigManager` object.

    Args:
        config (ConfigManager): The configuration manager instance to store the local path setting.

    Note:
        This function uses `click.prompt` to interact with the user, providing a default path (the current working directory)
        and validating the user's input to ensure it meets the criteria for an absolute path to a directory.\n    """\n\n    def get_default_path():\n        return os.getcwd()\n\n    while True:\n        default_path = get_default_path()\n        local_path = click.prompt(\n            "Enter the absolute path to your local project directory",\n            type=click.Path(\n                exists=True, file_okay=False, dir_okay=True, resolve_path=True\n            ),\n            default=default_path,\n            show_default=True,\n        )\n\n        if os.path.isabs(local_path):\n            config.set("local_path", local_path)\n            click.echo(f"Local path set to: {local_path}")\n            break\n        else:\n            click.echo("Please enter an absolute path.")\n\n\ndef load_claudeignore(base_path):\n    """\n    Loads and parses the .claudeignore file from the specified base path.\n\n    Args:\n        base_path (str): The base directory path where the .claudeignore file is located.\n\n    Returns:\n        pathspec.PathSpec or None: A PathSpec object containing the patterns from the .claudeignore file\n                                    if the file exists; otherwise, None.\n    """\n    claudeignore_path = os.path.join(base_path, ".claudeignore")\n    if os.path.exists(claudeignore_path):\n        with open(claudeignore_path, "r") as f:\n            return pathspec.PathSpec.from_lines("gitwildmatch", f)\n    return None