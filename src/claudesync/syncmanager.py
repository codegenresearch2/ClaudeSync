import os
import time
import logging
from datetime import datetime, timezone

import click
from tqdm import tqdm

from claudesync.utils import compute_md5_hash
from claudesync.exceptions import ProviderError

logger = logging.getLogger(__name__)

class SyncManager:
    """\n    Manages the synchronization process between local and remote files.\n    """

    def __init__(self, provider, config):
        """\n        Initialize the SyncManager with the given provider and configuration.\n\n        Args:\n            provider (Provider): The provider instance to interact with the remote storage.\n            config (dict): Configuration dictionary containing sync settings.\n        """
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

    def check_existing_remote_projects(self):
        """\n        Check for existing remote projects and handle any errors more robustly.\n        """
        try:
            projects = self.provider.get_projects(self.active_organization_id, include_archived=False)
            if not projects:
                click.echo("No active projects found. Please create a new project.")
                return
        except ProviderError as e:
            click.echo(f"Failed to retrieve projects: {str(e)}")
            return

    def retry_on_403(func):
        """\n        Decorator to retry a function on 403 Forbidden error.\n\n        This decorator will retry the wrapped function up to max_retries times\n        if a ProviderError with a 403 Forbidden message is encountered.\n        """

        def wrapper(self, *args, **kwargs):
            for attempt in range(self.max_retries):
                try:
                    return func(self, *args, **kwargs)
                except ProviderError as e:
                    if "403 Forbidden" in str(e) and attempt < self.max_retries - 1:
                        logger.warning(
                            f"Received 403 error. Retrying in {self.retry_delay} seconds..."
                        )
                        time.sleep(self.retry_delay)
                    else:
                        raise

        return wrapper

    # The rest of the code remains the same, as it already follows the provided rules.