import json
import logging
import os
import re

from tqdm import tqdm

from .exceptions import ConfigurationError

logger = logging.getLogger(__name__)

def save_chat_metadata(chat, chat_folder):
    """Save chat metadata to a JSON file."""
    metadata_file = os.path.join(chat_folder, "metadata.json")
    with open(metadata_file, "w") as f:
        json.dump(chat, f, indent=2)

def save_chat_messages(chat_folder, full_chat):
    """Save chat messages to separate JSON files."""
    for message in full_chat["chat_messages"]:
        message_file = os.path.join(chat_folder, f"{message['uuid']}.json")
        with open(message_file, "w") as f:
            json.dump(message, f, indent=2)

def save_artifacts(chat_folder, artifacts):
    """Save artifacts to separate files."""
    artifact_folder = os.path.join(chat_folder, "artifacts")
    os.makedirs(artifact_folder, exist_ok=True)
    for artifact in artifacts:
        artifact_file = os.path.join(artifact_folder, f"{artifact['identifier']}.{get_file_extension(artifact['type'])}")
        with open(artifact_file, "w") as f:
            f.write(artifact["content"])

def get_file_extension(artifact_type):
    """Get the appropriate file extension for a given artifact type."""
    type_to_extension = {
        "text/html": "html",
        "application/vnd.ant.code": "txt",
        "image/svg+xml": "svg",
        "application/vnd.ant.mermaid": "mmd",
        "application/vnd.ant.react": "jsx",
    }
    return type_to_extension.get(artifact_type, "txt")

def extract_artifacts(text):
    """Extract artifacts from the given text."""
    artifacts = []
    pattern = re.compile(
        r'<antArtifact\s+identifier="([^"]+)"\s+type="([^"]+)"\s+title="([^"]+)">([\s\S]*?)</antArtifact>',
        re.MULTILINE,
    )
    matches = pattern.findall(text)

    for match in matches:
        identifier, artifact_type, title, content = match
        artifacts.append(
            {
                "identifier": identifier,
                "type": artifact_type,
                "content": content.strip(),
            }
        )

    return artifacts

def sync_chats(provider, config, sync_all=False):
    """Synchronize chats and their artifacts from the remote source."""
    local_path = config.get("local_path")
    if not local_path:
        raise ConfigurationError("Local path not set. Use 'claudesync project select' or 'claudesync project create' to set it.")

    chat_destination = os.path.join(local_path, "claude_chats")
    os.makedirs(chat_destination, exist_ok=True)

    organization_id = config.get("active_organization_id")
    if not organization_id:
        raise ConfigurationError("No active organization set. Please select an organization.")

    active_project_id = config.get("active_project_id")
    if not active_project_id and not sync_all:
        raise ConfigurationError("No active project set. Please select a project or use the -a flag to sync all chats.")

    logger.debug(f"Fetching chats for organization {organization_id}")
    chats = provider.get_chat_conversations(organization_id)
    logger.debug(f"Found {len(chats)} chats")

    for chat in tqdm(chats, desc="Syncing chats"):
        if sync_all or (chat.get("project") and chat["project"].get("uuid") == active_project_id):
            chat_folder = os.path.join(chat_destination, chat["uuid"])
            if not os.path.exists(chat_folder):
                os.makedirs(chat_folder)
                logger.info(f"Processing new chat {chat['uuid']}")
                save_chat_metadata(chat, chat_folder)
                full_chat = provider.get_chat_conversation(organization_id, chat["uuid"])
                save_chat_messages(chat_folder, full_chat)
                artifacts = extract_artifacts(full_chat["chat_messages"][0]["text"])
                save_artifacts(chat_folder, artifacts)
            else:
                logger.debug(f"Skipping existing chat {chat['uuid']}")
        else:
            logger.debug(f"Skipping chat {chat['uuid']} as it doesn't belong to the active project")

    logger.debug(f"Chats and artifacts synchronized to {chat_destination}")