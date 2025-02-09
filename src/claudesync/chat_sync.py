import json
import logging
import os
import re

from tqdm import tqdm

from .exceptions import ConfigurationError

logger = logging.getLogger(__name__)

# Constants
LOCAL_PATH_KEY = "local_path"
ACTIVE_ORGANIZATION_ID_KEY = "active_organization_id"
ACTIVE_PROJECT_ID_KEY = "active_project_id"

def get_file_extension(artifact_type):
    type_to_extension = {
        "text/html": "html",
        "application/vnd.ant.code": "txt",
        "image/svg+xml": "svg",
        "application/vnd.ant.mermaid": "mmd",
        "application/vnd.ant.react": "jsx",
    }
    return type_to_extension.get(artifact_type, "txt")

def extract_artifacts(text):
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

def save_artifacts(chat_folder, artifacts):
    artifact_folder = os.path.join(chat_folder, "artifacts")
    os.makedirs(artifact_folder, exist_ok=True)
    for artifact in artifacts:
        artifact_file = os.path.join(
            artifact_folder, f"{artifact['identifier']}.{get_file_extension(artifact['type'])}"
        )
        if not os.path.exists(artifact_file):
            with open(artifact_file, "w") as f:
                f.write(artifact["content"])
            logger.info(f"Saved artifact {artifact['identifier']} in chat folder {chat_folder}")
        else:
            logger.debug(f"Skipping existing artifact {artifact['identifier']} in chat folder {chat_folder}")

def sync_chat(provider, config, chat_id, chat_destination):
    chat_folder = os.path.join(chat_destination, chat_id)
    os.makedirs(chat_folder, exist_ok=True)

    # Save chat metadata
    metadata_file = os.path.join(chat_folder, "metadata.json")
    if not os.path.exists(metadata_file):
        metadata = provider.get_chat_conversation(chat_id)
        with open(metadata_file, "w") as f:
            json.dump(metadata, f, indent=2)
        logger.info(f"Saved metadata for chat {chat_id}")
    else:
        logger.debug(f"Skipping existing metadata for chat {chat_id}")

    # Fetch and save chat messages
    messages_file = os.path.join(chat_folder, "messages.json")
    if not os.path.exists(messages_file):
        messages = provider.get_chat_messages(chat_id)
        with open(messages_file, "w") as f:
            json.dump(messages, f, indent=2)
        logger.info(f"Saved messages for chat {chat_id}")
    else:
        logger.debug(f"Skipping existing messages for chat {chat_id}")

    # Handle artifacts in assistant messages
    full_chat = provider.get_chat_conversation(chat_id)
    assistant_messages = [msg for msg in full_chat if msg["sender"] == "assistant"]
    if assistant_messages:
        logger.info(f"Found {len(assistant_messages)} assistant messages in chat {chat_id}")
        artifacts = extract_artifacts(full_chat)
        save_artifacts(chat_folder, artifacts)

def sync_chats(provider, config, sync_all=False):
    local_path = config.get(LOCAL_PATH_KEY)
    if not local_path:
        raise ConfigurationError(f"Local path not set. Use 'claudesync project select' or 'claudesync project create' to set it.")

    chat_destination = os.path.join(local_path, "claude_chats")
    os.makedirs(chat_destination, exist_ok=True)

    organization_id = config.get(ACTIVE_ORGANIZATION_ID_KEY)
    if not organization_id:
        raise ConfigurationError("No active organization set. Please select an organization.")

    active_project_id = config.get(ACTIVE_PROJECT_ID_KEY)
    if not active_project_id and not sync_all:
        raise ConfigurationError("No active project set. Please select a project or use the -a flag to sync all chats.")

    logger.debug(f"Fetching chats for organization {organization_id}")
    chats = provider.get_chat_conversations(organization_id)
    logger.debug(f"Found {len(chats)} chats")

    for chat in tqdm(chats, desc="Syncing chats"):
        if sync_all or (chat.get("project") and chat["project"].get("uuid") == active_project_id):
            logger.info(f"Processing chat {chat['uuid']}")
            sync_chat(provider, config, chat["uuid"], chat_destination)
        else:
            logger.debug(f"Skipping chat {chat['uuid']} as it doesn't belong to the active project")

    logger.debug(f"Chats and artifacts synchronized to {chat_destination}")