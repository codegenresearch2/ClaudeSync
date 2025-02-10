import json
import logging
import os
import re

from tqdm import tqdm

from .exceptions import ConfigurationError

logger = logging.getLogger(__name__)

# Constants for file paths and names
CHAT_DESTINATION = "chats"
METADATA_FILE_NAME = "metadata.json"

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

    organization_id = config.get("active_organization_id")
    if not organization_id:
        raise ConfigurationError("No active organization set. Please select an organization.")

    active_project_id = config.get("active_project_id")
    if not active_project_id and not sync_all:
        raise ConfigurationError("No active project set. Please select a project or use the -a flag to sync all chats.")

    chat_destination = os.path.join(local_path, CHAT_DESTINATION)
    os.makedirs(chat_destination, exist_ok=True)

    logger.debug(f"Fetching chats for organization {organization_id}")
    chats = provider.get_chat_conversations(organization_id)
    logger.debug(f"Found {len(chats)} chats")

    for chat in tqdm(chats, desc="Syncing chats"):
        chat_id = chat["uuid"]
        chat_folder = os.path.join(chat_destination, chat_id)
        os.makedirs(chat_folder, exist_ok=True)

        if not sync_all and chat.get("project") and chat["project"].get("uuid") != active_project_id:
            logger.debug(f"Skipping chat {chat_id} as it doesn't belong to the active project")
            continue

        logger.info(f"Processing chat {chat_id}")

        metadata_file = os.path.join(chat_folder, METADATA_FILE_NAME)
        if not os.path.exists(metadata_file):
            with open(metadata_file, "w") as f:
                json.dump(chat, f, indent=2)

        full_chat = provider.get_chat_conversation(organization_id, chat_id)
        for message in full_chat["chat_messages"]:
            message_file = os.path.join(chat_folder, f"{message['uuid']}.json")
            if not os.path.exists(message_file):
                with open(message_file, "w") as f:
                    json.dump(message, f, indent=2)

            if message["sender"] == "assistant":
                artifacts = extract_artifacts(message["text"])
                if artifacts:
                    logger.info(f"Found {len(artifacts)} artifacts in message {message['uuid']}")
                    save_artifacts(artifacts, chat_folder)

    logger.debug(f"Chats and artifacts synchronized to {chat_destination}")


def save_artifacts(artifacts, chat_folder):
    """
    Save artifacts to the specified chat folder.

    Args:
        artifacts (list): List of artifacts to save.
        chat_folder (str): The folder where the artifacts should be saved.
    """
    artifact_folder = os.path.join(chat_folder, "artifacts")
    os.makedirs(artifact_folder, exist_ok=True)

    for artifact in artifacts:
        file_extension = get_file_extension(artifact["type"])
        artifact_file = os.path.join(artifact_folder, f"{artifact['identifier']}.{file_extension}")
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