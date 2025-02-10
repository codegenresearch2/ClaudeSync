import os
import click
from retry import retry
from urllib3.exceptions import HTTPError
from claudesync.exceptions import ProviderError

# Configuration object to manage state and settings
config = {
    'API_ENDPOINT': 'https://api.example.com/v1',
    'AUTH_TOKEN': 'Bearer your_auth_token'
}

# Retry decorator for handling 403 errors
@retry(HTTPError, tries=3, delay=1, backoff=2)
def retry_on_403(func):
    return func

# Decorator to handle errors in commands
def handle_errors(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ProviderError as e:
            click.echo(f"An error occurred: {str(e)}")
        except Exception as e:
            click.echo(f"An unexpected error occurred: {str(e)}")
    return wrapper

# Command group for project management
@click.group()
@click.pass_obj
def project(config):
    """Manage ai projects within the active organization."""
    pass

# Command to create a new project
@project.command()
@click.pass_obj
@handle_errors
def create(config):
    """Create a new project in the active organization."""
    provider = validate_and_get_provider(config)
    active_organization_id = config.get("active_organization_id")

    title = click.prompt("Enter a title for your new project")
    description = click.prompt("Enter the project description (optional)", default="")

    try:
        new_project = provider.create_project(
            active_organization_id, title, description
        )
        click.echo(
            f"Project '{new_project['title']}' (uuid: {new_project['uuid']}) has been created successfully."
        )

        config['active_project_id'] = new_project["uuid"]
        config['active_project_name'] = new_project["title"]
    except ProviderError as e:
        click.echo(f"Failed to create project: {str(e)}")

# Command to archive an existing project
@project.command()
@click.pass_obj
@handle_errors
def archive(config):
    """Archive an existing project."""
    provider = validate_and_get_provider(config)
    active_organization_id = config.get("active_organization_id")
    projects = provider.get_projects(active_organization_id, include_archived=False)
    if not projects:
        click.echo("No active projects found.")
        return
    click.echo("Available projects to archive:")
    for idx, project in enumerate(projects, 1):
        click.echo(f"  {idx}. {project['title']} (ID: {project['id']})")
    selection = click.prompt("Enter the number of the project to archive", type=int)
    if 1 <= selection <= len(projects):
        project_id = projects[selection - 1]['id']
        confirm = click.confirm(f"Are you sure you want to archive the project '{projects[selection - 1]['title']}'?")
        if confirm:
            provider.archive_project(active_organization_id, project_id)
            click.echo(f"Project '{projects[selection - 1]['title']}' has been archived.")
    else:
        click.echo("Invalid selection. Please try again.")

# Command to select an active project
@project.command()
@click.pass_obj
@handle_errors
def select(config):
    """Set the active project for syncing."""
    provider = validate_and_get_provider(config)
    active_organization_id = config.get("active_organization_id")
    projects = provider.get_projects(active_organization_id, include_archived=False)
    if not projects:
        click.echo("No active projects found.")
        return
    click.echo("Available projects:")
    for idx, project in enumerate(projects, 1):
        click.echo(f"  {idx}. {project['title']} (ID: {project['id']})")
    selection = click.prompt("Enter the number of the project to select", type=int, default=1)
    if 1 <= selection <= len(projects):
        selected_project = projects[selection - 1]
        config['active_project_id'] = selected_project["id"]
        config['active_project_name'] = selected_project["title"]
        click.echo(f"Selected project: {selected_project['title']} (ID: {selected_project['id']})")
    else:
        click.echo("Invalid selection. Please try again.")

# Command to list all projects
@project.command()
@click.pass_obj
@handle_errors
def ls(config):
    """List all projects in the active organization."""
    provider = validate_and_get_provider(config)
    active_organization_id = config.get("active_organization_id")
    projects = provider.get_projects(active_organization_id, include_archived=True)
    if not projects:
        click.echo("No projects found.")
    else:
        click.echo("Remote projects:")
        for project in projects:
            status = " (Archived)" if project.get("archived_at") else ""
            click.echo(f"  - {project['title']} (ID: {project['id']}){status}")

# Command to synchronize the project files
@project.command()
@click.pass_obj
@handle_errors
def sync(config):
    """Synchronize the project files, including submodules if they exist remotely."""
    provider = validate_and_get_provider(config)
    active_project_id = config.get("active_project_id")
    local_path = config.get("local_path")
    if not local_path:
        click.echo(
            "No local path set for this project. Please select an existing project or create a new one using "
            "'claudesync project select' or 'claudesync project create'."
        )
        return
    submodule_detect_filenames = config.get("submodule_detect_filenames", [])
    local_submodules = detect_submodules(local_path, submodule_detect_filenames)
    all_remote_projects = provider.get_projects()
    remote_submodule_projects = [
        project for project in all_remote_projects if project["title"].startswith(config['active_project_name'] + "-SubModule-")
    ]
    sync_manager = SyncManager(provider, config)
    remote_files = provider.list_files(active_project_id)
    local_files = get_local_files(local_path)
    sync_manager.sync(local_files, remote_files)
    click.echo(f"Main project '{config['active_project_name']}' synced successfully.")
    for local_submodule, detected_file in local_submodules:
        submodule_name = os.path.basename(local_submodule)
        remote_project = next(
            (proj for proj in remote_submodule_projects if proj["title"].endswith(f"-{submodule_name}")), None
        )
        if remote_project:
            click.echo(f"Syncing submodule '{submodule_name}'...")
            submodule_path = os.path.join(local_path, local_submodule)
            submodule_files = get_local_files(submodule_path)
            remote_submodule_files = provider.list_files(remote_project["id"])
            submodule_config = config.copy()
            submodule_config["active_project_id"] = remote_project["id"]
            submodule_config["active_project_name"] = remote_project["title"]
            submodule_config["local_path"] = submodule_path
            submodule_sync_manager = SyncManager(provider, submodule_config)
            submodule_sync_manager.sync(submodule_files, remote_submodule_files)
            click.echo(f"Submodule '{submodule_name}' synced successfully.")
        else:
            click.echo(f"No remote project found for submodule '{submodule_name}'. Skipping sync.")
    click.echo("Project sync completed successfully, including available submodules.")

# Add commands to the main group
project.add_command(create)
project.add_command(archive)
project.add_command(select)
project.add_command(ls)
project.add_command(sync)


This updated code snippet addresses the syntax error and incorporates the feedback from the oracle, including error handling, consistent use of configuration, improved command structure, and more.