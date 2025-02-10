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
def create(config):
    """Create new projects for each detected submodule that doesn't already exist remotely."""
    try:
        import requests
    except ModuleNotFoundError:
        click.echo("Error: The 'requests' library is not installed. Please install it using 'pip install requests'.")
        return

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

    # Fetch all remote projects
    all_remote_projects = provider.get_projects(active_organization_id, include_archived=False)

    click.echo(f"Detected {len(submodules)} submodule(s). Creating projects for each:")

    for i, submodule in enumerate(submodules, 1):
        submodule_name = os.path.basename(submodule)
        new_project_name = f"{active_project_name}-SubModule-{submodule_name}"

        # Check if the project already exists remotely
        if any(project["name"] == new_project_name for project in all_remote_projects):
            click.echo(f"{i}. Project '{new_project_name}' already exists remotely. Skipping creation.")
            continue

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

In the updated code, I have added a check for the presence of the `requests` library at the beginning of the `create` function. If the library is not found, the function will display an error message and return, preventing the code from executing further.

I have also added a step to fetch all remote projects using the `provider.get_projects` method. This allows the code to check if a project for a submodule already exists remotely before creating a new one.

The output messages have been refined to provide clear feedback to the user, indicating when a project already exists and when the project creation process is completed.

The function's docstring has been updated to accurately describe its functionality, which is creating projects for submodules that don't already exist remotely.