import os\\\nimport click\\\\\nfrom claudesync.utils import get_local_files\\\\nfrom ..utils import handle_errors, validate_and_get_provider\\\\nfrom ..syncmanager import SyncManager\\\\nfrom ..chat_sync import sync_chats\\\\n\\\\n@click.command()\\\\n@click.pass_obj\\\\n@handle_errors\\\\ndef sync(config):\"\"\"Synchronize both projects and chats.\"\"\"\\\\n    provider = validate_and_get_provider(config)\\\\n\\\\n    # Sync projects\\\\n    sync_manager = SyncManager(provider, config)\\\\n    remote_files = provider.list_files(\\\n        sync_manager.active_organization_id, sync_manager.active_project_id\\\\n    )\\\\n    local_files = get_local_files(config.get("local_path"))\\\\n    sync_manager.sync(local_files, remote_files)\\\\n    click.echo("Project sync completed successfully.")\\\\n\\\\n    # Sync chats\\\\n    sync_chats(provider, config)\\\\n    click.echo("Chat sync completed successfully.")\\\\n\\\\nif __name__ == '__main__':\\\\n    sync()