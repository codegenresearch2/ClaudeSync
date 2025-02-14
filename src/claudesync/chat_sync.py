import json
import logging
import os
import re

from tqdm import tqdm

from .exceptions import ConfigurationError

logger = logging.getLogger(__name__)


def sync_chats(provider, config, sync_all=False):
    local_path = config.get("local_path")
    if not local_path:
        raise ConfigurationError("Local path not set.")

    chat_destination = os.path.join(local_path, "chats")
    os.makedirs(chat_destination, exist_ok=True)

    organization_id = config.get("active_organization_id")
    if not organization_id:
        raise ConfigurationError("No active organization set.")

    active_project_id = config.get("active_project_id")
    if not active_project_id and not sync_all:
        raise ConfigurationError("No active project set.")

    logger.debug(f"Fetching chats for organization {organization_id}")
    chats = provider.get_chat_conversations(organization_id)
    logger.debug(f"Found {len(chats)} chats")

    for chat in tqdm(chats, desc="Syncing chats"):
        if sync_all or (chat.get("project") and chat["project"].get("uuid") == active_project_id):
            logger.info(f"Processing chat {chat['uuid']}")
            chat_folder = os.path.join(chat_destination, chat["uuid"])
            os.makedirs(chat_folder, exist_ok=True)

            with open(os.path.join(chat_folder, "metadata.json"), "w") as f:
                json.dump(chat, f, indent=2)

            logger.debug(f"Fetching full conversation for chat {chat['uuid']}")
            full_chat = provider.get_chat_conversation(organization_id, chat["uuid"])

            for message in full_chat["chat_messages"]:
                message_file = os.path.join(chat_folder, f"{message['uuid']}.json")
                with open(message_file, "w") as f:
                    json.dump(message, f, indent=2)

                if message["sender"] == "assistant":
                    artifacts = extract_artifacts(message["text"])
                    if artifacts:
                        logger.info(f"Found {len(artifacts)} artifacts in message {message['uuid']}")
                        artifact_folder = os.path.join(chat_folder, "artifacts")
                        os.makedirs(artifact_folder, exist_ok=True)
                        for artifact in artifacts:
                            artifact_file = os.path.join(artifact_folder, f"{artifact['identifier']}.{get_file_extension(artifact['type'])}")
                            with open(artifact_file, "w") as f:
                                f.write(artifact["content"])
        else:
            logger.debug(f"Skipping chat {chat['uuid']} as it doesn't belong to the active project")

    logger.debug(f"Chats and artifacts synchronized to {chat_destination}")


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