import json
import logging
import os
import re

from tqdm import tqdm

from .exceptions import ConfigurationError

logger = logging.getLogger(__name__)


def save_artifacts(chat_folder, artifacts):
    """Save artifacts to the specified chat folder."""
    artifact_folder = os.path.join(chat_folder, "artifacts")
    os.makedirs(artifact_folder, exist_ok=True)
    for artifact in artifacts:
        artifact_file = os.path.join(artifact_folder, f"{artifact['identifier']}.{get_file_extension(artifact['type'])}")
        with open(artifact_file, "w") as f:
            f.write(artifact["content"])


def extract_artifacts(text):
    """
    Extract artifacts from the given text.

    This function searches for antArtifact tags in the text and extracts
    the artifact information, including identifier, type, and content.

    Args:
        text (str): The text to search for artifacts.

    Returns:
        list: A list of dictionaries containing artifact information.
    """
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


def sync_chat(provider, config, chat, chat_destination):
    """Synchronize a single chat and its artifacts."""
    chat_folder = os.path.join(chat_destination, chat["uuid"])
    os.makedirs(chat_folder, exist_ok=True)

    # Save chat metadata
    with open(os.path.join(chat_folder, "metadata.json"), "w") as f:
        json.dump(chat, f, indent=2)

    # Fetch full chat conversation
    logger.debug(f"Fetching full conversation for chat {chat['uuid']}")
    full_chat = provider.get_chat_conversation(chat["organization_id"], chat["uuid"])

    # Save each message
    for message in full_chat["chat_messages"]:
        message_file = os.path.join(chat_folder, f"{message['uuid']}.json")
        with open(message_file, "w") as f:
            json.dump(message, f, indent=2)

    # Handle artifacts in assistant messages
    if full_chat["sender"] == "assistant":
        artifacts = extract_artifacts(full_chat["text"])
        if artifacts:
            logger.info(f"Found {len(artifacts)} artifacts in chat {chat['uuid']}")
            save_artifacts(chat_folder, artifacts)


def sync_chats(provider, config, sync_all=False):
    """
    Synchronize chats and their artifacts from the remote source.

    This function fetches all chats for the active organization, saves their metadata,
    messages, and extracts any artifacts found in the assistant's messages.

    Args:
        provider: The API provider instance.
        config: The configuration manager instance.
        sync_all (bool): If True, sync all chats regardless of project. If False, only sync chats for the active project.

    Raises:
        ConfigurationError: If required configuration settings are missing.
    """
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
            logger.info(f"Processing chat {chat['uuid']}")
            sync_chat(provider, config, chat, chat_destination)
        else:
            logger.debug(f"Skipping chat {chat['uuid']} as it doesn't belong to the active project")

    logger.debug(f"Chats and artifacts synchronized to {chat_destination}")