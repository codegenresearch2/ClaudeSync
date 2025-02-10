import os
import logging
import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import RequestException
from urllib3.util.retry import Retry
import click
from claudesync.exceptions import ProviderError
from ..utils import (
    handle_errors,
    validate_and_get_provider,
    detect_submodules,
)

logger = logging.getLogger(__name__)

def retry_on_request_exception(retries=3, backoff_factor=0.3, status_forcelist=(500, 502, 504)):
    def decorator(func):
        def wrapper(*args, **kwargs):
            session = requests.Session()
            retry = Retry(total=retries, backoff_factor=backoff_factor, status_forcelist=status_forcelist)
            adapter = HTTPAdapter(max_retries=retry)
            session.mount('http://', adapter)
            session.mount('https://', adapter)
            kwargs['session'] = session
            return func(*args, **kwargs)
        return wrapper
    return decorator

@click.group()
def submodule():
    """Manage submodules within the current project."""
    pass

@submodule.command()
@click.pass_obj
@handle_errors
def ls(config):
    """List all detected submodules in the current project."""
    local_path = config.get("local_path")
    if not local_path:
        click.echo(
            "No local path set for this project. Please select an existing project or create a new one using "
            "'claudesync project select' or 'claudesync project create'."
        )
        return

    submodule_detect_filenames = config.get("submodule_detect_filenames", [])
    submodules = detect_submodules(local_path, submodule_detect_filenames)

    if not submodules:
        click.echo("No submodules detected in the current project.")
    else:
        click.echo("Detected submodules:")
        for submodule, detected_file in submodules:
            click.echo(f"  - {submodule} [{detected_file}]")

@submodule.command()
@click.pass_obj
@handle_errors
def create(config):
    """Create new projects for each detected submodule."""
    provider = validate_and_get_provider(config, require_project=True)
    active_organization_id = config.get("active_organization_id")
    active_project_id = config.get("active_project_id")
    active_project_name = config.get("active_project_name")
    local_path = config.get("local_path")

    if not local_path:
        click.echo(
            "No local path set for this project. Please select an existing project or create a new one using "
            "'claudesync project select' or 'claudesync project create'."
        )
        return

    submodule_detect_filenames = config.get("submodule_detect_filenames", [])
    submodules_with_files = detect_submodules(local_path, submodule_detect_filenames)

    # Extract only the submodule paths from the list of tuples
    submodules = [submodule for submodule, _ in submodules_with_files]

    if not submodules:
        click.echo("No submodules detected in the current project.")
        return

    click.echo(f"Detected {len(submodules)} submodule(s). Creating projects for each:")

    for i, submodule in enumerate(submodules, 1):
        submodule_name = os.path.basename(submodule)
        new_project_name = f"{active_project_name}-SubModule-{submodule_name}"
        description = f"Submodule '{submodule_name}' for project '{active_project_name}' (ID: {active_project_id})"

        try:
            new_project = create_project_with_retry(provider, active_organization_id, new_project_name, description)
            click.echo(
                f"{i}. Created project '{new_project_name}' (ID: {new_project['uuid']}) for submodule '{submodule_name}'"
            )
        except ProviderError as e:
            logger.error(f"Failed to create project for submodule '{submodule_name}': {str(e)}")
            click.echo(
                f"Failed to create project for submodule '{submodule_name}': {str(e)}"
            )

    click.echo(
        "\nSubmodule projects created successfully. You can now select and sync these projects individually."
    )

@retry_on_request_exception()
def create_project_with_retry(provider, organization_id, name, description, session=None):
    try:
        return provider.create_project(organization_id, name, description, session=session)
    except RequestException as e:
        logger.error(f"HTTP request failed: {str(e)}")
        raise ProviderError(f"Failed to create project: {str(e)}")