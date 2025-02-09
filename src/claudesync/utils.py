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
    """
    Normalizes the line endings of the input content to Unix-style (\n) and calculates the MD5 checksum of the normalized content.

    This function normalizes the line endings of the input content to Unix-style (\n),
    strips leading and trailing whitespace, and then calculates the MD5 checksum of the normalized content.
    This is useful for ensuring consistent checksums across different environments.

    Args:
        content (str): The content for which to calculate the MD5 checksum.

    Returns:
        str: The hexadecimal MD5 checksum of the normalized content.
    """
    normalized_content = content.replace('\r\n', '\n').replace('\r', '\n').strip()
    return hashlib.md5(normalized_content.encode('utf-8')).hexdigest()

def load_gitignore(base_path):
    """
    Loads and parses the .gitignore file from the specified base path.

    This function attempts to find a .gitignore file in the given base path.
    If found, it reads the file and creates a PathSpec object that can be used to match paths
    against the patterns defined in the .gitignore file.

    Args:
        base_path (str): The base directory path where the .gitignore file is located.

    Returns:
        pathspec.PathSpec or None: A PathSpec object containing the patterns from the .gitignore file
                                    if the file exists; otherwise, None.
    """
    gitignore_path = os.path.join(base_path, '.gitignore')
    if os.path.exists(gitignore_path):
        with open(gitignore_path, 'r') as f:
            return pathspec.PathSpec.from_lines('gitwildmatch', f)
    return None

def is_text_file(file_path, sample_size=8192):
    """
    Determines if a file is a text file by checking for the absence of null bytes.

    This function reads a sample of the file (default 8192 bytes) and checks if it contains any null byte (\x00).
    The presence of a null byte is often indicative of a binary file.

    Args:
        file_path (str): The path to the file to be checked.
        sample_size (int, optional): The number of bytes to read from the file for checking.

    Returns:
        bool: True if the file is likely a text file, False if it is likely binary or an error occurred.
    """
    try:
        with open(file_path, 'rb') as file:
            return b'\x00' not in file.read(sample_size)
    except IOError:
        return False

def process_file(file_path):
    """
    Reads the content of a file and computes its MD5 hash.

    This function attempts to read the file as UTF-8 text and compute its MD5 hash.
    If the file cannot be read as UTF-8 or any other error occurs, it logs the issue and returns None.

    Args:
        file_path (str): The path to the file to be processed.

    Returns:
        str or None: The MD5 hash of the file's content if successful, None otherwise.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            return normalize_and_calculate_md5(content)
    except UnicodeDecodeError:
        logger.debug(f'Unable to read {file_path} as UTF-8 text. Skipping.')
    except Exception as e:
        logger.error(f'Error reading file {file_path}: {str(e)}')
    return None

def get_local_files(local_path):
    gitignore = load_gitignore(local_path)
    claudeignore = load_claudeignore(local_path)
    files = {}
    exclude_dirs = {'.git', '.svn', '.hg', '.bzr', '_darcs', 'CVS'}
    for root, dirs, filenames in os.walk(local_path):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        rel_root = os.path.relpath(root, local_path)
        rel_root = '' if rel_root == '.' else rel_root
        for filename in filenames:
            rel_path = os.path.join(rel_root, filename)
            full_path = os.path.join(root, filename)
            if should_process_file(full_path, filename, gitignore, local_path, claudeignore):
                file_hash = process_file(full_path)
                if file_hash:
                    files[rel_path] = file_hash
    return files

@handle_errors
def validate_and_get_provider(config, require_org=True):
    active_provider = config.get('active_provider')
    session_key = config.get('session_key')
    if not active_provider or not session_key:
        raise ConfigurationError('No active provider or session key. Please login first.')
    if require_org and not config.get('active_organization_id'):
        raise ConfigurationError('No active organization set. Please select an organization.')
    return get_provider(active_provider, session_key)

# Assuming the function `validate_and_store_local_path` is defined elsewhere
# and should be implemented or imported as per the feedback.

# Implementing or importing `validate_and_store_local_path` as per feedback:

def validate_and_store_local_path(config):
    """
    Prompts the user for the absolute path to their local project directory and stores it in the configuration.

    This function repeatedly prompts the user to enter the absolute path to their local project directory until
    a valid absolute path is provided. The path is validated to ensure it is an absolute path to a directory.
    Once a valid path is provided, it is stored in the configuration using the `set` method of the `ConfigManager` object.

    Args:
        config (ConfigManager): The configuration manager instance to store the local path setting.
    """
    while True:
        local_path = click.prompt(
            'Enter the absolute path to your local project directory',
            type=click.Path(exists=True, file_okay=False, dir_okay=True, resolve_path=True)
        )
        if os.path.isabs(local_path):
            config.set('local_path', local_path)
            click.echo(f'Local path set to: {local_path}')
            break
        else:
            click.echo('Please enter an absolute path.')
