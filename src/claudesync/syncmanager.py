import os
import time
import logging
from datetime import datetime, timezone

from tqdm import tqdm

from claudesync.utils import compute_md5_hash
from claudesync.chat_sync import process_chat_directory

logger = logging.getLogger(__name__)

# Define constants
UPLOAD_DELAY = 0.5

class SyncManager:
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
        self.upload_delay = config.get("upload_delay", UPLOAD_DELAY)
        self.two_way_sync = config.get("two_way_sync", False)

    def sync(self, local_files, remote_files):
        """
        Main synchronization method that orchestrates the sync process.

        Args:
            local_files (dict): Dictionary of local file names and their corresponding checksums.
            remote_files (list): List of dictionaries representing remote files.
        """
        remote_files_to_delete = set(rf["file_name"] for rf in remote_files)
        synced_files = set()

        with tqdm(total=len(local_files), desc="Syncing local to remote") as pbar:
            for local_file, local_checksum in local_files.items():
                if local_file.endswith('.chat'):
                    process_chat_directory(self.provider, self.config, local_file)
                else:
                    self.sync_file(local_file, local_checksum, remote_files, remote_files_to_delete, synced_files)
                pbar.update(1)

        self.update_local_timestamps(remote_files, synced_files)

        if self.two_way_sync:
            with tqdm(total=len(remote_files), desc="Syncing remote to local") as pbar:
                for remote_file in remote_files:
                    self.sync_remote_to_local(remote_file, remote_files_to_delete, synced_files)
                    pbar.update(1)

        with tqdm(total=len(remote_files_to_delete), desc="Deleting remote files") as pbar:
            for file_to_delete in list(remote_files_to_delete):
                self.delete_remote_files(file_to_delete, remote_files)
                pbar.update(1)

        logger.info("Sync completed successfully.")

    def sync_file(self, local_file, local_checksum, remote_files, remote_files_to_delete, synced_files):
        """
        Synchronize a file between local and remote storage.

        Args:
            local_file (str): Name of the local file.
            local_checksum (str): MD5 checksum of the local file content.
            remote_files (list): List of dictionaries representing remote files.
            remote_files_to_delete (set): Set of remote file names to be considered for deletion.
            synced_files (set): Set of file names that have been synchronized.
        """
        remote_file = next((rf for rf in remote_files if rf["file_name"] == local_file), None)
        if remote_file:
            self.update_existing_file(local_file, local_checksum, remote_file, remote_files_to_delete, synced_files)
        else:
            self.upload_new_file(local_file, synced_files)

    # Rest of the methods remain the same

def process_chat_directory(provider, config, chat_directory):
    """
    Process a chat directory and perform synchronization.

    Args:
        provider (Provider): The provider instance to interact with the remote storage.
        config (dict): Configuration dictionary containing sync settings.
        chat_directory (str): Name of the chat directory.
    """
    # Implement chat processing logic here
    pass