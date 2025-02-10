import os
import logging

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

logging.basicConfig(level=logging.INFO)

@click.group()
def project():
    """Manage ai projects within the active organization."""
    pass

@project.command()
@click.pass_obj
@handle_errors
def create(config):
    """Create a new project in the active organization."""
    provider = validate_and_get_provider(config)
    active_organization_id = config.get("active_organization_id")

    default_name = os.path.basename(os.getcwd())
    title = click.prompt("Enter a title for your new project", default=default_name)
    description = click.prompt("Enter the project description (optional)", default="")

    try:
        new_project = provider.create_project(
            active_organization_id, title, description
        )
        logging.info(f"Project '{new_project['name']}' (uuid: {new_project['uuid']}) has been created successfully.")

        config.set("active_project_id", new_project["uuid"])
        config.set("active_project_name", new_project["name"])
        logging.info(f"Active project set to: {new_project['name']} (uuid: {new_project['uuid']})")

        validate_and_store_local_path(config)

    except ProviderError as e:
        logging.error(f"Failed to create project: {str(e)}")

@project.command()
@click.pass_obj
@handle_errors
def archive(config):
    """Archive an existing project."""
    provider = validate_and_get_provider(config)
    active_organization_id = config.get("active_organization_id")
    projects = provider.get_projects(active_organization_id, include_archived=False)
    if not projects:
        logging.info("No active projects found.")
        return
    click.echo("Available projects to archive:")
    for idx, project in enumerate(projects, 1):
        click.echo(f"  {idx}. {project['name']} (ID: {project['id']})")
    selection = click.prompt("Enter the number of the project to archive", type=int)
    if 1 <= selection <= len(projects):
        selected_project = projects[selection - 1]
        if click.confirm(
            f"Are you sure you want to archive the project '{selected_project['name']}'?"
            f"Archived projects cannot be modified but can still be viewed."
        ):
            provider.archive_project(active_organization_id, selected_project["id"])
            logging.info(f"Project '{selected_project['name']}' has been archived.")
    else:
        logging.warning("Invalid selection. Please try again.")

@project.command()
@click.option(
    "-a",
    "--all",
    "show_all",
    is_flag=True,
    help="Include submodule projects in the selection",
)
@click.pass_context
@handle_errors
def select(ctx, show_all):
    """Set the active project for syncing."""
    config = ctx.obj
    provider = validate_and_get_provider(config)
    active_organization_id = config.get("active_organization_id")
    active_project_name = config.get("active_project_name")
    projects = provider.get_projects(active_organization_id, include_archived=False)

    if show_all:
        selectable_projects = projects
    else:
        selectable_projects = [p for p in projects if "-SubModule-" not in p["name"]]

    if not selectable_projects:
        logging.info("No active projects found.")
        return

    click.echo("Available projects:")
    for idx, project in enumerate(selectable_projects, 1):
        project_type = (
            "Main Project"
            if not project["name"].startswith(f"{active_project_name}-SubModule-")
            else "Submodule"
        )
        click.echo(f"  {idx}. {project['name']} (ID: {project['id']}) - {project_type}")

    selection = click.prompt(
        "Enter the number of the project to select", type=int, default=1
    )
    if 1 <= selection <= len(selectable_projects):
        selected_project = selectable_projects[selection - 1]
        config.set("active_project_id", selected_project["id"])
        config.set("active_project_name", selected_project["name"])
        logging.info(f"Selected project: {selected_project['name']} (ID: {selected_project['id']})")

        validate_and_store_local_path(config)
    else:
        logging.warning("Invalid selection. Please try again.")

@project.command()
@click.option(
    "-a",
    "--all",
    "show_all",
    is_flag=True,
    help="Include archived projects in the list",
)
@click.pass_obj
@handle_errors
def ls(config, show_all):
    """List all projects in the active organization."""
    provider = validate_and_get_provider(config)
    active_organization_id = config.get("active_organization_id")
    projects = provider.get_projects(active_organization_id, include_archived=show_all)
    if not projects:
        logging.info("No projects found.")
    else:
        logging.info("Remote projects:")
        for project in projects:
            status = " (Archived)" if project.get("archived_at") else ""
            logging.info(f"  - {project['name']} (ID: {project['id']}){status}")

@project.command()
@click.option("--category", help="Specify the file category to sync")
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
        logging.warning(
            "No local path set for this project. Please select an existing project or create a new one using "
            "'claudesync project select' or 'claudesync project create'."
        )
        return

    submodule_detect_filenames = config.get("submodule_detect_filenames", [])
    local_submodules = detect_submodules(local_path, submodule_detect_filenames)

    all_remote_projects = provider.get_projects(
        active_organization_id, include_archived=False
    )

    remote_submodule_projects = [
        project
        for project in all_remote_projects
        if project["name"].startswith(f"{active_project_name}-SubModule-")
    ]

    sync_manager = SyncManager(provider, config)
    remote_files = provider.list_files(active_organization_id, active_project_id)
    local_files = get_local_files(local_path, category)
    sync_manager.sync(local_files, remote_files)
    logging.info(f"Main project '{active_project_name}' synced successfully.")

    for local_submodule, detected_file in local_submodules:
        submodule_name = os.path.basename(local_submodule)
        remote_project = next(
            (
                proj
                for proj in remote_submodule_projects
                if proj["name"].endswith(f"-{submodule_name}")
            ),
            None,
        )

        if remote_project:
            logging.info(f"Syncing submodule '{submodule_name}'...")
            submodule_path = os.path.join(local_path, local_submodule)
            submodule_files = get_local_files(submodule_path, category)
            remote_submodule_files = provider.list_files(
                active_organization_id, remote_project["id"]
            )

            submodule_config = config.config.copy()
            submodule_config["active_project_id"] = remote_project["id"]
            submodule_config["active_project_name"] = remote_project["name"]
            submodule_config["local_path"] = submodule_path
            submodule_sync_manager = SyncManager(provider, submodule_config)

            submodule_sync_manager.sync(submodule_files, remote_submodule_files)
            logging.info(f"Submodule '{submodule_name}' synced successfully.")
        else:
            logging.warning(
                f"No remote project found for submodule '{submodule_name}'. Skipping sync."
            )

    logging.info("Project sync completed successfully, including available submodules.")

project.add_command(submodule)