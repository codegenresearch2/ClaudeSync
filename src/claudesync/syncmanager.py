import functools
import time
import logging
from datetime import datetime, timezone
import os

import click
from tqdm import tqdm

from claudesync.utils import compute_md5_hash
from claudesync.exceptions import ProviderError

# Initialize logger at the module level
logger = logging.getLogger(__name__)

def retry_on_403(max_retries=3, delay=1):
    """
    Decorator to retry a function on 403 Forbidden error.

    This decorator will retry the wrapped function up to max_retries times
    if a ProviderError with a 403 Forbidden message is encountered.

    Args:
        max_retries (int): Maximum number of retries for 403 errors.
        delay (int): Delay between retries in seconds.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Handle the case where self might not be available
            instance = args[0] if args else None
            logger_to_use = getattr(instance, 'logger', logger)

            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except ProviderError as e:
                    if "403 Forbidden" in str(e) and attempt < max_retries - 1:
                        logger_to_use.warning(f"Received 403 error, retrying in {delay} seconds...")
                        time.sleep(delay)
                    else:
                        raise
        return wrapper
    return decorator

class SyncManager:
    """
    Manages the synchronization process between local and remote files.
    """

    def __init__(self, provider, config):
        """
        Initialize the SyncManager with the given provider and configuration.

        Args:
            provider (Provider): The provider instance to interact with the remote storage.
            config (dict): Configuration dictionary containing sync settings.
        """
        self.provider = provider
        self.config = config
        self.active_organization_id = config.get("active_organization_id")
        self.active_project_id = config.get("active_project_id")
        self.local_path = config.get("local_path")
        self.upload_delay = config.get("upload_delay", 0.5)
        self.two_way_sync = config.get("two_way_sync", False)
        self.max_retries = 3  # Maximum number of retries for 403 errors
        self.retry_delay = 1  # Delay between retries in seconds

        # Check for existing remote projects
        self.check_existing_remote_projects()

    @retry_on_403
    def check_existing_remote_projects(self):
        """
        Check for existing remote projects and handle any errors more robustly.
        """
        projects = self.provider.get_projects(self.active_organization_id, include_archived=False)
        if not projects:
            logger.info("No active projects found. Please create a new project.")

    # Rest of the code remains the same