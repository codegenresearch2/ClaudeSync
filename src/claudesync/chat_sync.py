import logging

logger = logging.getLogger(__name__)

def sync_chats(provider, config):
    """
    Synchronize chats and their artifacts from the remote source.

    This function fetches all chats for the active organization, saves their metadata,
    messages, and extracts any artifacts found in the assistant's messages.

    Args:
        provider: The API provider instance.
        config: The configuration manager instance.

    Raises:
        ConfigurationError: If required configuration settings are missing.
    """
    # Implementation of sync_chats function
    pass

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
    # Implementation of extract_artifacts function
    pass