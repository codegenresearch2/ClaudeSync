import logging\"import json\"import os\"import re\"import tqdm\"\n\nfrom .exceptions import ConfigurationError\n\nlogger = logging.getLogger(__name__)\n\n\ndef sync_chats(provider, config, sync_all=False):\n    \"\"\n    Synchronize chats and their artifacts from the remote source.\n\n    This function fetches all chats for the active organization, saves their metadata, messages, and extracts any artifacts found in the assistant's messages.\n\n    Args:\n        provider: The API provider instance.\n        config: The configuration manager instance.\n        sync_all (bool): If True, sync all chats regardless of project. If False, only sync chats for the active project.\n\n    Raises:\n        ConfigurationError: If required configuration settings are missing.\n    \"\"\n    # Get the local_path for chats\n    local_path = config.get("local_path")\n    if not local_path:\n        raise ConfigurationError(\"Local path not set. Use 'claudesync project select' or 'claudesync project create' to set it.\")\n\n    # Create chats directory within local_path\n    chat_destination = os.path.join(local_path, "chats")\n    os.makedirs(chat_destination, exist_ok=True)\n\n    # Get the active organization ID\n    organization_id = config.get("active_organization_id")\n    if not organization_id:\n        raise ConfigurationError(\"No active organization set. Please select an organization.\")\n\n    # Get the active project ID\n    active_project_id = config.get("active_project_id")\n    if not active_project_id and not sync_all:\n        raise ConfigurationError(\"No active project set. Please select a project or use the -a flag to sync all chats.\")\n\n    # Fetch all chats for the organization\n    logger.debug(f"Fetching chats for organization {organization_id}")\n    chats = provider.get_chat_conversations(organization_id)\n    logger.debug(f"Found {len(chats)} chats")\n\n    # Process each chat\n    for chat in tqdm(chats, desc="Syncing chats"):\n        # Check if the chat belongs to the active project or if we're syncing all chats\n        if sync_all or (chat.get("project") and chat["project"].get("uuid") == active_project_id):\n            logger.info(f"Processing chat {chat['uuid']}")\n            chat_folder = os.path.join(chat_destination, chat["uuid"])\n            os.makedirs(chat_folder, exist_ok=True)\n\n            # Save chat metadata\n            with open(os.path.join(chat_folder, "metadata.json"), "w") as f:\n                json.dump(chat, f, indent=2)\n\n            # Fetch full chat conversation\n            logger.debug(f"Fetching full conversation for chat {chat['uuid']}")\n            full_chat = provider.get_chat_conversation(organization_id, chat["uuid"])\n\n            # Process each message in the chat\n            for message in full_chat["chat_messages"]:\n                # Save the message\n                message_file = os.path.join(chat_folder, f"{message['uuid']}.json")\n                with open(message_file, "w") as f:\n                    json.dump(message, f, indent=2)\n\n                # Handle artifacts in assistant messages\n                if message["sender"] == "assistant":\n                    artifacts = extract_artifacts(message["text"])\n                    if artifacts:\n                        logger.info(f"Found {len(artifacts)} artifacts in message {message['uuid']}")\n                        artifact_folder = os.path.join(chat_folder, "artifacts")\n                        os.makedirs(artifact_folder, exist_ok=True)\n                        for artifact in artifacts:\n                            # Save each artifact\n                            artifact_file = os.path.join(\n                                artifact_folder,\n                                f"{artifact['identifier']}.{get_file_extension(artifact['type'])}"\\)                            with open(artifact_file, "w") as f:\n                                f.write(artifact["content"])\n        else:\n            logger.debug(f"Skipping chat {chat['uuid']} as it doesn't belong to the active project")\n\n    logger.debug(f"Chats and artifacts synchronized to {chat_destination}")\n\n\ndef get_file_extension(artifact_type):\n    \"\"\n    Get the appropriate file extension for a given artifact type.\n\n    Args:\n        artifact_type (str): The MIME type of the artifact.\n\n    Returns:\n        str: The corresponding file extension.\n    \"\"\n    type_to_extension = {\n        "text/html": "html",\n        "application/vnd.ant.code": "txt",\n        "image/svg+xml": "svg",\n        "application/vnd.ant.mermaid": "mmd",\n        "application/vnd.ant.react": "jsx",\n    }\n    return type_to_extension.get(artifact_type, "txt")