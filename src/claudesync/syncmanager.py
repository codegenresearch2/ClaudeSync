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

        # Check if there are any existing remote projects
        self.check_existing_remote_projects()

    def retry_on_403(func):
        """\n        Decorator to retry a function on 403 Forbidden error.\n\n        This decorator will retry the wrapped function up to max_retries times\n        if a ProviderError with a 403 Forbidden message is encountered.\n        """

        def wrapper(self, *args, **kwargs):
            for attempt in range(self.max_retries):
                try:
                    return func(self, *args, **kwargs)
                except ProviderError as e:
                    if "403 Forbidden" in str(e):
                        if attempt < self.max_retries - 1:
                            logger.warning(
                                f"Received 403 error. Retrying in {self.retry_delay} seconds..."
                            )
                            time.sleep(self.retry_delay)
                        else:
                            click.echo(f"Failed to perform the operation after {self.max_retries} attempts. Please check your permissions.")
                            return
                    else:
                        raise

        return wrapper

    def check_existing_remote_projects(self):
        """\n        Check if there are any existing remote projects.\n\n        This method will prompt the user to select an existing project or create a new one.\n        """
        projects = self.provider.get_projects(self.active_organization_id, include_archived=False)
        if not projects:
            click.echo("No existing remote projects found. Please create a new project.")
        else:
            click.echo("Available remote projects:")
            for idx, project in enumerate(projects, 1):
                click.echo(f"  {idx}. {project['name']} (ID: {project['id']})")
            selection = click.prompt(
                "Enter the number of the project to select or '0' to create a new one", type=int, default=0
            )
            if selection == 0:
                self.create_new_project()
            elif 1 <= selection <= len(projects):
                selected_project = projects[selection - 1]
                self.config.set("active_project_id", selected_project["id"])
                self.config.set("active_project_name", selected_project["name"])
                click.echo(
                    f"Selected project: {selected_project['name']} (ID: {selected_project['id']})"
                )
            else:
                click.echo("Invalid selection. Please try again.")

    def create_new_project(self):
        """\n        Create a new project in the active organization.\n        """
        title = click.prompt("Enter a title for your new project", default=os.path.basename(os.getcwd()))
        description = click.prompt("Enter the project description (optional)", default="")

        try:
            new_project = self.provider.create_project(
                self.active_organization_id, title, description
            )
            click.echo(
                f"Project '{new_project['name']}' (uuid: {new_project['uuid']}) has been created successfully."
            )
            self.config.set("active_project_id", new_project["uuid"])
            self.config.set("active_project_name", new_project["name"])
            click.echo(
                f"Active project set to: {new_project['name']} (uuid: {new_project['uuid']})"
            )
        except ProviderError as e:
            click.echo(f"Failed to create project: {str(e)}")

    # Rest of the code remains the same

The rewritten code includes modifications to handle existing remote projects, robustly handle HTTP errors, and provide clearer feedback during project creation. The `check_existing_remote_projects` method checks for existing remote projects and allows the user to select an existing project or create a new one. The `create_new_project` method handles project creation and provides clearer feedback to the user. The `retry_on_403` decorator has been enhanced to provide a more detailed message when the maximum number of retries is exceeded for a 403 Forbidden error.