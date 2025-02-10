import os
import time
import logging
from datetime import datetime, timezone

from tqdm import tqdm

from claudesync.utils import compute_md5_hash

logger = logging.getLogger(__name__)

class SyncManager:
    def __init__(self, provider, config):
        self.provider = provider
        self.config = config
        self.active_organization_id = config.get("active_organization_id")
        self.active_project_id = config.get("active_project_id")
        self.local_path = config.get("local_path")
        self.upload_delay = config.get("upload_delay", 0.5)
        self.two_way_sync = config.get("two_way_sync", False)

    def sync(self, local_files, remote_files):
        remote_files_to_delete = set(rf["file_name"] for rf in remote_files)
        synced_files = set()

        print("Syncing local to remote...")
        for local_file, local_checksum in local_files.items():
            remote_file = next((rf for rf in remote_files if rf["file_name"] == local_file), None)
            if remote_file:
                self.update_existing_file(local_file, local_checksum, remote_file, remote_files_to_delete, synced_files)
            else:
                self.upload_new_file(local_file, synced_files)

        print("Updating local timestamps...")
        self.update_local_timestamps(remote_files, synced_files)

        if self.two_way_sync:
            print("Syncing remote to local...")
            for remote_file in remote_files:
                self.sync_remote_to_local(remote_file, remote_files_to_delete, synced_files)

        print("Deleting remote files...")
        for file_to_delete in list(remote_files_to_delete):
            self.delete_remote_files(file_to_delete, remote_files)

    def update_existing_file(self, local_file, local_checksum, remote_file, remote_files_to_delete, synced_files):
        remote_checksum = compute_md5_hash(remote_file["content"])
        if local_checksum != remote_checksum:
            print(f"Updating {local_file} on remote...")
            self.provider.delete_file(self.active_organization_id, self.active_project_id, remote_file["uuid"])
            with open(os.path.join(self.local_path, local_file), "r", encoding="utf-8") as file:
                content = file.read()
            self.provider.upload_file(self.active_organization_id, self.active_project_id, local_file, content)
            time.sleep(self.upload_delay)
            synced_files.add(local_file)
        remote_files_to_delete.remove(local_file)

    def upload_new_file(self, local_file, synced_files):
        print(f"Uploading new file {local_file} to remote...")
        with open(os.path.join(self.local_path, local_file), "r", encoding="utf-8") as file:
            content = file.read()
        self.provider.upload_file(self.active_organization_id, self.active_project_id, local_file, content)
        time.sleep(self.upload_delay)
        synced_files.add(local_file)

    def update_local_timestamps(self, remote_files, synced_files):
        for remote_file in remote_files:
            if remote_file["file_name"] in synced_files:
                local_file_path = os.path.join(self.local_path, remote_file["file_name"])
                if os.path.exists(local_file_path):
                    remote_timestamp = datetime.fromisoformat(remote_file["created_at"].replace("Z", "+00:00")).timestamp()
                    os.utime(local_file_path, (remote_timestamp, remote_timestamp))
                    print(f"Updated timestamp on local file {local_file_path}")

    def sync_remote_to_local(self, remote_file, remote_files_to_delete, synced_files):
        local_file_path = os.path.join(self.local_path, remote_file["file_name"])
        if os.path.exists(local_file_path):
            self.update_existing_local_file(local_file_path, remote_file, remote_files_to_delete, synced_files)
        else:
            self.create_new_local_file(local_file_path, remote_file, remote_files_to_delete, synced_files)

    def update_existing_local_file(self, local_file_path, remote_file, remote_files_to_delete, synced_files):
        local_mtime = datetime.fromtimestamp(os.path.getmtime(local_file_path), tz=timezone.utc)
        remote_mtime = datetime.fromisoformat(remote_file["created_at"].replace("Z", "+00:00"))
        if remote_mtime > local_mtime:
            print(f"Updating local file {remote_file['file_name']} from remote...")
            with open(local_file_path, "w", encoding="utf-8") as file:
                file.write(remote_file["content"])
            synced_files.add(remote_file["file_name"])
            if remote_file["file_name"] in remote_files_to_delete:
                remote_files_to_delete.remove(remote_file["file_name"])

    def create_new_local_file(self, local_file_path, remote_file, remote_files_to_delete, synced_files):
        print(f"Creating new local file {remote_file['file_name']} from remote...")
        with open(local_file_path, "w", encoding="utf-8") as file:
            file.write(remote_file["content"])
        synced_files.add(remote_file["file_name"])
        if remote_file["file_name"] in remote_files_to_delete:
            remote_files_to_delete.remove(remote_file["file_name"])

    def delete_remote_files(self, file_to_delete, remote_files):
        print(f"Deleting {file_to_delete} from remote...")
        remote_file = next(rf for rf in remote_files if rf["file_name"] == file_to_delete)
        self.provider.delete_file(self.active_organization_id, self.active_project_id, remote_file["uuid"])
        time.sleep(self.upload_delay)