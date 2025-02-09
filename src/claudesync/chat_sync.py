import json
import logging
import os
import re
from tqdm import tqdm
from .exceptions import ConfigurationError

logger = logging.getLogger(__name__)

# Helper function to save artifacts
def save_artifacts(chat_folder, artifacts):
    artifact_folder = os.path.join(chat_folder, 'artifacts')
os.makedirs(artifact_folder, exist_ok=True)
    for artifact in artifacts:
        artifact_file = os.path.join(
            artifact_folder,
            f"{artifact['identifier']}.{get_file_extension(artifact['type'])}"
        )
        if not os.path.exists(artifact_file):
            with open(artifact_file, 'w') as f:
                f.write(artifact['content'])

# Function to sync a single chat
def sync_chat(provider, config, chat):
    chat_destination = config.get('local_path', '') + '/chats'
os.makedirs(chat_destination, exist_ok=True)
    chat_folder = os.path.join(chat_destination, chat['uuid'])
os.makedirs(chat_folder, exist_ok=True)

    # Save chat metadata
    with open(os.path.join(chat_folder, 'metadata.json'), 'w') as f:
        json.dump(chat, f, indent=2)

    # Fetch full chat conversation
    full_chat = provider.get_chat_conversation(chat['organization_id'], chat['uuid'])

    # Process each message in the chat
    for message in full_chat['chat_messages']:
        message_file = os.path.join(chat_folder, f'{message['uuid']}.json')
        if not os.path.exists(message_file):
            with open(message_file, 'w') as f:
                json.dump(message, f, indent=2)
        if message['sender'] == 'assistant':
            artifacts = extract_artifacts(message['text'])
            if artifacts:
                logger.info(f'Found {len(artifacts)} artifacts in message {message['uuid']}')
                save_artifacts(chat_folder, artifacts)

# Main function to sync all chats
def sync_chats(provider, config, sync_all=False):
    local_path = config.get('local_path')
    if not local_path:
        raise ConfigurationError(
            'Local path not set. Use claudesync project select or claudesync project create to set it.'
        )

    organization_id = config.get('active_organization_id')
    if not organization_id:
        raise ConfigurationError(
            'No active organization set. Please select an organization.'
        )

    active_project_id = config.get('active_project_id')
    if not active_project_id and not sync_all:
        raise ConfigurationError(
            'No active project set. Please select a project or use the -a flag to sync all chats.'
        )

    logger.debug(f'Fetching chats for organization {organization_id}')
    chats = provider.get_chat_conversations(organization_id)
    logger.debug(f'Found {len(chats)} chats')

    for chat in tqdm(chats, desc='Syncing chats'):
        sync_chat(provider, config, chat)

    logger.debug(f'Chats synchronized to {local_path}/chats')

# Helper function to get file extension from artifact type
def get_file_extension(artifact_type):
    type_to_extension = {
        'text/html': 'html',
        'application/vnd.ant.code': 'txt',
        'image/svg+xml': 'svg',
        'application/vnd.ant.mermaid': 'mmd',
        'application/vnd.ant.react': 'jsx',
    }
    return type_to_extension.get(artifact_type, 'txt')

# Helper function to extract artifacts from text
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
                'identifier': identifier,
                'type': artifact_type,
                'content': content.strip(),
            }
        )
    return artifacts
