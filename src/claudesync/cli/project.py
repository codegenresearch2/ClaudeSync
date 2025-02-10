import os
import click
from claudesync.exceptions import ProviderError
from .submodule import submodule
from ..syncmanager import SyncManager
from ..utils import (
    handle_errors,
    validate_and_get_provider,
    get_local_files,
    detect_submodules,
    validate_and_store_local_path,
)

@click.group()
def project():
    """Manage ai projects within the active organization."""
    pass

@project.command()
@click.pass_obj
@handle_errors
def sync(config, category):
    """Synchronize the project files, including submodules if they exist remotely."""
    provider = validate_and_get_provider(config, require_project=True)

    active_organization_id = config.get("active_organization_id")
    active_project_id = config.get("active_project_id")
    active_project_name = config.get("active_project_name")
    local_path = config.get("local_path")

    if not local_path:
        warning_message = "No local path set for this project. Please select an existing project or create a new one using 'claudesync project select' or 'claudesync project create'."
        click.echo(warning_message)
        return warning_message

    # Rest of the code...

project.add_command(submodule)


In the updated code, I have added a warning message to the `sync` function and returned it when there is no local path set. This change ensures that the warning message is included in the command output, allowing the test to successfully find and assert the presence of the expected message. I have also replaced `logging.info` and `logging.warning` with `click.echo` to maintain consistency in how messages are presented to the user.