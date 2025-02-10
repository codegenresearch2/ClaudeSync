import json
import logging
import os
import re

from tqdm import tqdm

from .exceptions import ConfigurationError

logger = logging.getLogger(__name__)


def save_artifacts(artifacts, chat_folder, message):
    """
    Save artifacts to the specified chat folder.

    Args:
        artifacts (list): A list of dictionaries containing artifact information.
        chat_folder (str): The folder where the artifacts will be saved.
        message (dict): The message metadata.
    """
    if not artifacts:
        return

    artifact_folder = os.path.join(chat_folder, "artifacts")
    os.makedirs(artifact_folder, exist_ok=True)
    for artifact in artifacts:
        artifact_file = os.path.join(
            artifact_folder,
            f"{artifact['identifier']}.{get_file_extension(artifact['type'])}",
        )
        if not os.path.exists(artifact_file):
            with open(artifact_file, "w") as f:
                f.write(artifact["content"])
            logger.info(f"Saved artifact {artifact['identifier']} in message {message['uuid']}")
        else:
            logger.debug(f"Artifact {artifact['identifier']} already exists, skipping.")


def process_message(provider, config, chat_folder, message, organization_id):
    """
    Process a single message and save its content if it's an assistant message.

    Args:
        provider: The API provider instance.
        config: The configuration manager instance.
        chat_folder (str): The folder where the message will be saved.
        message (dict): The message metadata.
        organization_id (str): The ID of the organization.
    """
    message_file = os.path.join(chat_folder, f"{message['uuid']}.json")
    if not os.path.exists(message_file):
        with open(message_file, "w") as f:
            json.dump(message, f, indent=2)
        logger.info(f"Saved message {message['uuid']}")

        if message["sender"] == "assistant":
            artifacts = extract_artifacts(message["text"])
            if artifacts:
                logger.info(f"Found {len(artifacts)} artifacts in message {message['uuid']}")
                save_artifacts(artifacts, chat_folder, message)
    else:
        logger.debug(f"Message {message['uuid']} already exists, skipping.")


def fetch_full_chat(provider, organization_id, chat_id):
    """
    Fetch the full chat conversation for a given chat ID.

    Args:
        provider: The API provider instance.
        organization_id (str): The ID of the organization.
        chat_id (str): The ID of the chat.

    Returns:
        dict: The full chat conversation.
    """
    return provider.get_chat_conversation(organization_id, chat_id)


def sync_chat(provider, config, chat, organization_id, project_id):
    """
    Synchronize a single chat and its artifacts.

    Args:
        provider: The API provider instance.
        config: The configuration manager instance.
        chat (dict): The chat metadata.
        organization_id (str): The ID of the organization.
        project_id (str): The ID of the project.
    """
    chat_folder = os.path.join(config.get("local_path"), "claude_chats", chat["uuid"])
    
    # Check if the chat folder already exists
    if os.path.exists(chat_folder):
        logger.debug(f"Chat folder {chat_folder} already exists, skipping.")
        return
    
    os.makedirs(chat_folder, exist_ok=True)

    # Save chat metadata
    with open(os.path.join(chat_folder, "metadata.json"), "w") as f:
        json.dump(chat, f, indent=2)
    logger.info(f"Saved chat metadata for {chat['uuid']}")

    # Fetch full chat conversation
    full_chat = fetch_full_chat(provider, organization_id, chat["uuid"])

    # Process each message in the chat
    for message in full_chat["chat_messages"]:
        process_message(provider, config, chat_folder, message, organization_id)


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
        raise ConfigurationError(
            "Local path not set. Use 'claudesync project select' or 'claudesync project create' to set it."
        )

    organization_id = config.get("active_organization_id")
    if not organization_id:
        raise ConfigurationError(
            "No active organization set. Please select an organization."
        )

    project_id = config.get("active_project_id")
    if not project_id and not sync_all:
        raise ConfigurationError(
            "No active project set. Please select a project or use the -a flag to sync all chats."
        )

    chat_destination = os.path.join(local_path, "claude_chats")
    os.makedirs(chat_destination, exist_ok=True)

    logger.debug(f"Fetching chats for organization {organization_id}")
    chats = provider.get_chat_conversations(organization_id)
    logger.debug(f"Found {len(chats)} chats")

    for chat in tqdm(chats, desc="Syncing chats"):
        if sync_all or (
            chat.get("project") and chat["project"].get("uuid") == project_id
        ):
            logger.info(f"Processing chat {chat['uuid']}")
            sync_chat(provider, config, chat, organization_id, project_id)
        else:
            logger.debug(
                f"Skipping chat {chat['uuid']} as it doesn't belong to the active project"
            )

    logger.debug(f"Chats and artifacts synchronized to {chat_destination}")


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