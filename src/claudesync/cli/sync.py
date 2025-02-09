import os
import shutil
import sys
import click
from crontab import CronTab

from claudesync.utils import get_local_files
from ..utils import handle_errors, validate_and_get_provider
from ..syncmanager import SyncManager
from ..chat_sync import sync_chats
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

@click.group()
@click.pass_context
def cli(ctx):
    """ClaudeSync: Synchronize local files with ai projects."""
    ctx.obj = ConfigManager()

@cli.command()
@click.argument(
    'shell',
    required=False,
    type=click.Choice(['bash', 'zsh', 'fish', 'powershell'])
)
def install_completion(shell):
    """Install completion for the specified shell."""
    if shell is None:
        shell = click_completion.get_auto_shell()
        click.echo(f'Shell is set to \'{shell}\'')  # Corrected string formatting
    click_completion.install(shell=shell)
    click.echo('Completion installed.')

@cli.command()
@click.pass_obj
@handle_errors
def status(config):
    """Display current configuration status."""
    for key in [
        'active_provider',
        'active_organization_id',
        'active_project_id',
        'active_project_name',
        'local_path',
        'log_level']:
        value = config.get(key)
        click.echo(f'{key.replace('_', ' ').capitalize()}: {value or 'Not set'}')

@cli.command()
@click.pass_obj
@handle_errors
def ls(config):
    """List files in the active remote project."""
    provider = validate_and_get_provider(config)
    active_organization_id = config.get('active_organization_id')
    active_project_id = config.get('active_project_id')
    files = provider.list_files(active_organization_id, active_project_id)
    if not files:
        click.echo('No files found in the active project.')
    else:
        click.echo(
            f'Files in project \'{config.get('active_project_name')}\' (ID: {active_project_id}):')
        for file in files:
            click.echo(
                f'  - {file['file_name']} (ID: {file['uuid']}, Created: {file['created_at']})')

@cli.command()
@click.pass_obj
@handle_errors
def sync(config):
    """Synchronize both projects and chats."""
    provider = validate_and_get_provider(config)

    # Sync projects
    sync_manager = SyncManager(provider, config)
    remote_files = provider.list_files(
        sync_manager.active_organization_id, sync_manager.active_project_id)
    local_files = get_local_files(config.get('local_path'))
    sync_manager.sync(local_files, remote_files)
    click.echo('Project sync completed successfully.')

    # Sync chats
    sync_chats(provider, config)
    click.echo('Chat sync completed successfully.')

if __name__ == '__main__':
    cli()