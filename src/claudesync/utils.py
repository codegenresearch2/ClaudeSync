import os
import hashlib
import pathspec
import logging
from functools import wraps
from claudesync.exceptions import ConfigurationError, ProviderError
from claudesync.provider_factory import get_provider
from claudesync.config_manager import ConfigManager
import click

logger = logging.getLogger(__name__)
config_manager = ConfigManager()


def handle_errors(func):
    """Decorator to handle errors in functions."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (ConfigurationError, ProviderError) as e:
            logger.error(f'Error in {func.__name__}: {str(e)}')
            click.echo(f'Error: {str(e)}')
            raise
    return wrapper


def compute_md5_hash(content):
    """Computes the MD5 hash of the given content."
    return hashlib.md5(content.encode('utf-8')).hexdigest()


def load_gitignore(base_path):
    """Loads and parses the .gitignore file from the specified base path."
    gitignore_path = os.path.join(base_path, '.gitignore')
    if os.path.exists(gitignore_path):
        with open(gitignore_path, 'r') as f:
            return pathspec.PathSpec.from_lines('gitwildmatch', f)
    return None


def load_claudeignore(base_path):
    """Loads and parses the .claudeignore file from the specified base path."
    claudeignore_path = os.path.join(base_path, '.claudeignore')
    if os.path.exists(claudeignore_path):
        with open(claudeignore_path, 'r') as f:
            return pathspec.PathSpec.from_lines('gitwildmatch', f)
    return None


def is_text_file(file_path, sample_size=8192):
    """Determines if a file is a text file by checking for the absence of null bytes."
    try:
        with open(file_path, 'rb') as file:
            return b'\x00' not in file.read(sample_size)
    except IOError:
        return False


@handle_errors
def process_file(file_path):
    """Reads the content of a file and computes its MD5 hash."
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            return compute_md5_hash(content)
    except UnicodeDecodeError:
        logger.debug(f'Unable to read {file_path} as UTF-8 text. Skipping.')
    except Exception as e:
        logger.error(f'Error reading file {file_path}: {str(e)}')
    return None


@handle_errors
def get_local_files(local_path):
    """Retrieves a dictionary of local files within a specified path, applying various filters."
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
def should_process_file(file_path, filename, gitignore, base_path, claudeignore):
    """Determines whether a file should be processed based on various criteria."
    max_file_size = config_manager.get('max_file_size', 32 * 1024)
    if os.path.getsize(file_path) > max_file_size:
        return False
    if filename.endswith('~'):
        return False
    rel_path = os.path.relpath(file_path, base_path)
    if gitignore and gitignore.match_file(rel_path):
        return False
    if claudeignore and claudeignore.match_file(rel_path):
        return False
    return is_text_file(file_path)


@handle_errors
def validate_and_store_local_path(config):
    """Prompts the user for the absolute path to their local project directory and stores it in the configuration."
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
