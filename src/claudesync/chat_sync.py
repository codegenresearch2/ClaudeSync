import json
import logging
import os
import re

from tqdm import tqdm

from .exceptions import ConfigurationError

logger = logging.getLogger(__name__)

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

    chat_destination = os.path.join(local_path, "chats")
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
        sync_chat(provider, config, chat, chat_destination, active_project_id, sync_all)

    logger.debug(f"Chats and artifacts synchronized to {chat_destination}")

def sync_chat(provider, config, chat, chat_destination, active_project_id, sync_all):
    """
    Synchronize a single chat and its artifacts.

    Args:
        provider: The API provider instance.
        config: The configuration manager instance.
        chat: The chat metadata.
        chat_destination: The local directory to save the chat data.
        active_project_id: The ID of the active project.
        sync_all: Whether to sync all chats or only the active project's chats.
    """
    chat_folder = os.path.join(chat_destination, chat["uuid"])
    if not os.path.exists(chat_folder):
        os.makedirs(chat_folder)
        save_chat_metadata(chat, chat_folder)

        logger.debug(f"Fetching full conversation for chat {chat['uuid']}")
        full_chat = provider.get_chat_conversation(organization_id, chat["uuid"])
        save_chat_messages(full_chat, chat_folder)
        handle_artifacts(full_chat, chat_folder)

def save_chat_metadata(chat, chat_folder):
    """
    Save chat metadata to a file.

    Args:
        chat: The chat metadata.
        chat_folder: The local directory to save the chat data.
    """
    metadata_file = os.path.join(chat_folder, "metadata.json")
    if not os.path.exists(metadata_file):
        with open(metadata_file, "w") as f:
            json.dump(chat, f, indent=2)

def save_chat_messages(full_chat, chat_folder):
    """
    Save chat messages to files.

    Args:
        full_chat: The full chat conversation.
        chat_folder: The local directory to save the chat data.
    """
    for message in full_chat["chat_messages"]:
        message_file = os.path.join(chat_folder, f"{message['uuid']}.json")
        if not os.path.exists(message_file):
            with open(message_file, "w") as f:
                json.dump(message, f, indent=2)

def handle_artifacts(full_chat, chat_folder):
    """
    Handle and save artifacts found in the chat messages.

    Args:
        full_chat: The full chat conversation.
        chat_folder: The local directory to save the chat data.
    """
    artifact_folder = os.path.join(chat_folder, "artifacts")
    os.makedirs(artifact_folder, exist_ok=True)

    for message in full_chat["chat_messages"]:
        if message["sender"] == "assistant":
            artifacts = extract_artifacts(message["text"])
            save_artifacts(artifacts, artifact_folder)

def save_artifacts(artifacts, artifact_folder):
    """
    Save a list of artifacts to files.

    Args:
        artifacts: A list of artifact dictionaries.
        artifact_folder: The local directory to save the artifacts.
    """
    for artifact in artifacts:
        artifact_file = os.path.join(artifact_folder, f"{artifact['identifier']}.{get_file_extension(artifact['type'])}")
        if not os.path.exists(artifact_file):
            with open(artifact_file, "w") as f:
                f.write(artifact["content"])

def get_file_extension(artifact_type):
    """
    Get the appropriate file extension for a given artifact type.

    Args:
        artifact_type (str): The MIME type of the artifact.

    Returns:
        str: The corresponding file extension.
    """
    type_to_extension = {
        "text/html": "html",
        "application/vnd.ant.code": "txt",
        "image/svg+xml": "svg",
        "application/vnd.ant.mermaid": "mmd",
        "application/vnd.ant.react": "jsx",
    }
    return type_to_extension.get(artifact_type, "txt")

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