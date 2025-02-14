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

    def sync(self, local_files, remote_files):
        """\n        Main synchronization method that orchestrates the sync process.\n\n        Args:\n            local_files (dict): Dictionary of local file names and their corresponding checksums.\n            remote_files (list): List of dictionaries representing remote files.\n        """
        remote_files_to_delete = set(rf["file_name"] for rf in remote_files)
        synced_files = set()

        with tqdm(total=len(local_files), desc="Local → Remote") as pbar:
            for local_file, local_checksum in local_files.items():
                remote_file = next(
                    (rf for rf in remote_files if rf["file_name"] == local_file), None
                )
                if remote_file:
                    self.update_existing_file(
                        local_file,
                        local_checksum,
                        remote_file,
                        remote_files_to_delete,
                        synced_files,
                    )
                else:
                    self.upload_new_file(local_file, synced_files)
                pbar.update(1)

        self.update_local_timestamps(remote_files, synced_files)

        if self.two_way_sync:
            with tqdm(total=len(remote_files), desc="Local ← Remote") as pbar:
                for remote_file in remote_files:
                    self.sync_remote_to_local(
                        remote_file, remote_files_to_delete, synced_files
                    )
                    pbar.update(1)

        self.prune_remote_files(remote_files, remote_files_to_delete)

    @retry_on_403
    def update_existing_file(
        self,
        local_file,
        local_checksum,
        remote_file,
        remote_files_to_delete,
        synced_files,
    ):
        """\n        Update an existing file on the remote if it has changed locally.\n\n        Args:\n            local_file (str): Name of the local file.\n            local_checksum (str): MD5 checksum of the local file content.\n            remote_file (dict): Dictionary representing the remote file.\n            remote_files_to_delete (set): Set of remote file names to be considered for deletion.\n            synced_files (set): Set of file names that have been synchronized.\n        """
        remote_checksum = compute_md5_hash(remote_file["content"])
        if local_checksum != remote_checksum:
            logger.debug(f"Updating {local_file} on remote...")
            with tqdm(total=2, desc=f"Updating {local_file}", leave=False) as pbar:
                self.provider.delete_file(
                    self.active_organization_id,
                    self.active_project_id,
                    remote_file["uuid"],
                )
                pbar.update(1)
                with open(
                    os.path.join(self.local_path, local_file), "r", encoding="utf-8"
                ) as file:
                    content = file.read()
                self.provider.upload_file(
                    self.active_organization_id,
                    self.active_project_id,
                    local_file,
                    content,
                )
                pbar.update(1)
            time.sleep(self.upload_delay)
            synced_files.add(local_file)
        remote_files_to_delete.remove(local_file)

    @retry_on_403
    def upload_new_file(self, local_file, synced_files):
        """\n        Upload a new file to the remote project.\n\n        Args:\n            local_file (str): Name of the local file to be uploaded.\n            synced_files (set): Set of file names that have been synchronized.\n        """
        logger.debug(f"Uploading new file {local_file} to remote...")
        with open(
            os.path.join(self.local_path, local_file), "r", encoding="utf-8"
        ) as file:
            content = file.read()
        with tqdm(total=1, desc=f"Uploading {local_file}", leave=False) as pbar:
            self.provider.upload_file(
                self.active_organization_id, self.active_project_id, local_file, content
            )
            pbar.update(1)
        time.sleep(self.upload_delay)
        synced_files.add(local_file)

    def update_local_timestamps(self, remote_files, synced_files):
        """\n        Update local file timestamps to match the remote timestamps.\n\n        Args:\n            remote_files (list): List of dictionaries representing remote files.\n            synced_files (set): Set of file names that have been synchronized.\n        """
        for remote_file in remote_files:
            if remote_file["file_name"] in synced_files:
                local_file_path = os.path.join(
                    self.local_path, remote_file["file_name"]
                )
                if os.path.exists(local_file_path):
                    remote_timestamp = datetime.fromisoformat(
                        remote_file["created_at"].replace("Z", "+00:00")
                    ).timestamp()
                    os.utime(local_file_path, (remote_timestamp, remote_timestamp))
                    logger.debug(f"Updated timestamp on local file {local_file_path}")

    def sync_remote_to_local(self, remote_file, remote_files_to_delete, synced_files):
        """\n        Synchronize a remote file to the local project (two-way sync).\n\n        Args:\n            remote_file (dict): Dictionary representing the remote file.\n            remote_files_to_delete (set): Set of remote file names to be considered for deletion.\n            synced_files (set): Set of file names that have been synchronized.\n        """
        local_file_path = os.path.join(self.local_path, remote_file["file_name"])
        if os.path.exists(local_file_path):
            self.update_existing_local_file(
                local_file_path, remote_file, remote_files_to_delete, synced_files
            )
        else:
            self.create_new_local_file(
                local_file_path, remote_file, remote_files_to_delete, synced_files
            )

    def update_existing_local_file(
        self, local_file_path, remote_file, remote_files_to_delete, synced_files
    ):
        """\n        Update an existing local file if the remote version is newer.\n\n        Args:\n            local_file_path (str): Path to the local file.\n            remote_file (dict): Dictionary representing the remote file.\n            remote_files_to_delete (set): Set of remote file names to be considered for deletion.\n            synced_files (set): Set of file names that have been synchronized.\n        """
        local_mtime = datetime.fromtimestamp(
            os.path.getmtime(local_file_path), tz=timezone.utc
        )
        remote_mtime = datetime.fromisoformat(
            remote_file["created_at"].replace("Z", "+00:00")
        )
        if remote_mtime > local_mtime:
            logger.debug(
                f"Updating local file {remote_file['file_name']} from remote..."
            )
            with open(local_file_path, "w", encoding="utf-8") as file:
                file.write(remote_file["content"])
            synced_files.add(remote_file["file_name"])
            if remote_file["file_name"] in remote_files_to_delete:
                remote_files_to_delete.remove(remote_file["file_name"])

    def create_new_local_file(
        self, local_file_path, remote_file, remote_files_to_delete, synced_files
    ):
        """\n        Create a new local file from a remote file.\n\n        Args:\n            local_file_path (str): Path to the new local file.\n            remote_file (dict): Dictionary representing the remote file.\n            remote_files_to_delete (set): Set of remote file names to be considered for deletion.\n            synced_files (set): Set of file names that have been synchronized.\n        """
        logger.debug(
            f"Creating new local file {remote_file['file_name']} from remote..."
        )
        with tqdm(
            total=1, desc=f"Creating {remote_file['file_name']}", leave=False
        ) as pbar:
            with open(local_file_path, "w", encoding="utf-8") as file:
                file.write(remote_file["content"])
            pbar.update(1)
        synced_files.add(remote_file["file_name"])
        if remote_file["file_name"] in remote_files_to_delete:
            remote_files_to_delete.remove(remote_file["file_name"])

    def prune_remote_files(self, remote_files, remote_files_to_delete):
        """\n        Delete remote files that no longer exist locally.\n\n        Args:\n            remote_files (list): List of dictionaries representing remote files.\n            remote_files_to_delete (set): Set of remote file names to be deleted.\n        """
        if not self.config.get("prune_remote_files"):
            click.echo("Remote pruning is not enabled.")
            return

        for file_to_delete in list(remote_files_to_delete):
            self.delete_remote_files(file_to_delete, remote_files)

    @retry_on_403
    def delete_remote_files(self, file_to_delete, remote_files):
        """\n        Delete a file from the remote project that no longer exists locally.\n\n        Args:\n            file_to_delete (str): Name of the remote file to be deleted.\n            remote_files (list): List of dictionaries representing remote files.\n        """
        logger.debug(f"Deleting {file_to_delete} from remote...")
        remote_file = next(
            rf for rf in remote_files if rf["file_name"] == file_to_delete
        )
        with tqdm(total=1, desc=f"Deleting {file_to_delete}", leave=False) as pbar:
            self.provider.delete_file(
                self.active_organization_id, self.active_project_id, remote_file["uuid"]
            )
            pbar.update(1)
        time.sleep(self.upload_delay)