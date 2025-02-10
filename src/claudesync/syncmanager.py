import os
import time
import logging
import functools
from datetime import datetime, timezone

import click
from tqdm import tqdm

from claudesync.utils import compute_md5_hash
from claudesync.exceptions import ProviderError

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
        def wrapper(self, *args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(self, *args, **kwargs)
                except ProviderError as e:
                    if "403 Forbidden" in str(e) and attempt < max_retries - 1:
                        logger.warning(
                            f"Received 403 error. Retrying in {delay} seconds... (Attempt {attempt + 1} of {max_retries})"
                        )
                        time.sleep(delay)
                    else:
                        logger.error(f"Failed to perform operation after {max_retries} attempts: {str(e)}")
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

        # Check for existing projects
        try:
            projects = self.provider.get_projects(self.active_organization_id, include_archived=False)
            if not projects:
                click.echo("No active projects found. Please create a project first.")
                return
        except ProviderError as e:
            logger.error(f"Failed to retrieve projects: {str(e)}")
            return

    # The rest of the SyncManager class methods remain unchanged

# The rest of the code remains unchanged