import json
import logging
import os
import re

from tqdm import tqdm

from .exceptions import ConfigurationError

logger = logging.getLogger(__name__)


def save_message(chat_folder, message):
    """
    Save a message to the specified chat folder.

    Args:
        chat_folder (str): The folder where the message will be saved.
        message (dict): The message to be saved.
    """
    message_file = os.path.join(chat_folder, f"{message['uuid']}.json")
    if not os.path.exists(message_file):
        with open(message_file, "w") as f:
            json.dump(message, f, indent=2)
    else:
        logger.info(f"Message file {message_file} already exists, skipping write.")


def save_artifacts(artifacts, chat_folder, message):
    """
    Save artifacts to the specified chat folder.

    Args:
        artifacts (list): A list of dictionaries containing artifact information.
        chat_folder (str): The folder where chat artifacts will be saved.
        message (dict): The message containing the artifacts.
    """
    artifact_folder = os.path.join(chat_folder, "artifacts")
    os.makedirs(artifact_folder, exist_ok=True)

    for artifact in artifacts:
        artifact_file = os.path.join(artifact_folder, f"{artifact['identifier']}.{get_file_extension(artifact['type'])}")
        if not os.path.exists(artifact_file):
            with open(artifact_file, "w") as f:
                f.write(artifact["content"])
        else:
            logger.info(f"Artifact file {artifact_file} already exists, skipping write.")


def process_chat_messages(provider, config, chat, chat_folder):
    """
    Process and save chat messages and artifacts.

    Args:
        provider: The API provider instance.
        config: The configuration manager instance.
        chat (dict): The chat metadata.
        chat_folder (str): The folder where the chat data will be saved.
    """
    # Fetch full chat conversation
    logger.debug(f"Fetching full conversation for chat {chat['uuid']}")
    full_chat = provider.get_chat_conversation(chat["organization_id"], chat["uuid"])

    # Process each message in the chat
    for message in full_chat["chat_messages"]:
        if message["sender"] == "assistant":
            artifacts = extract_artifacts(message["text"])
            logger.info(f"Found {len(artifacts)} artifacts in message {message['uuid']}")
            save_artifacts(artifacts, chat_folder, message)
        save_message(chat_folder, message)


def sync_chat(provider, config, chat_id, organization_id):
    """
    Synchronize a single chat and its artifacts.

    Args:
        provider: The API provider instance.
        config: The configuration manager instance.
        chat_id (str): The ID of the chat to synchronize.
        organization_id (str): The ID of the organization the chat belongs to.
    """
    chat_folder = os.path.join(config.get("local_path"), "chats", chat_id)
    os.makedirs(chat_folder, exist_ok=True)

    # Check if chat metadata already exists
    metadata_file = os.path.join(chat_folder, "metadata.json")
    if not os.path.exists(metadata_file):
        # Save chat metadata
        chat = provider.get_chat_conversation(organization_id, chat_id)
        with open(metadata_file, "w") as f:
            json.dump(chat, f, indent=2)

    process_chat_messages(provider, config, chat, chat_folder)


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

    logger.debug(f"Fetching chats for organization {organization_id}")
    chats = provider.get_chat_conversations(organization_id)
    logger.debug(f"Found {len(chats)} chats")

    for chat in tqdm(chats, desc="Syncing chats"):
        if sync_all or (chat.get("project") and chat["project"].get("uuid") == config.get("active_project_id")):
            sync_chat(provider, config, chat["uuid"], organization_id)

    logger.debug(f"Chats and artifacts synchronized to {local_path}/chats")


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