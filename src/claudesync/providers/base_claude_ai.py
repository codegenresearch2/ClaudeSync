import datetime
import logging
import urllib.request
import urllib.parse
import gzip
import io
import json
import click
from abc import ABC, abstractmethod


class BaseProvider(ABC):
    @abstractmethod
    def login(self):
        """Authenticate with the provider and return a session key."""
        pass

    @abstractmethod
    def get_organizations(self):
        """Retrieve a list of organizations the user is a member of."""
        pass

    @abstractmethod
    def get_projects(self, organization_id, include_archived=False):
        """Retrieve a list of projects for a specified organization."""
        pass

    @abstractmethod
    def list_files(self, organization_id, project_id):
        """List all files within a specified project and organization."""
        pass

    @abstractmethod
    def upload_file(self, organization_id, project_id, file_name, content):
        """Upload a file to a specified project within an organization."""
        pass

    @abstractmethod
    def delete_file(self, organization_id, project_id, file_uuid):
        """Delete a file from a specified project within an organization."""
        pass

    @abstractmethod
    def archive_project(self, organization_id, project_id):
        """Archive a specified project within an organization."""
        pass

    @abstractmethod
    def create_project(self, organization_id, name, description=""):
        """Create a new project within a specified organization."""
        pass

    @abstractmethod
    def get_chat_conversations(self, organization_id):
        """Retrieve a list of chat conversations for a specified organization."""
        pass

    @abstractmethod
    def get_published_artifacts(self, organization_id):
        """Retrieve a list of published artifacts for a specified organization."""
        pass

    @abstractmethod
    def get_chat_conversation(self, organization_id, conversation_id):
        """Retrieve the full content of a specific chat conversation."""
        pass

    @abstractmethod
    def get_artifact_content(self, organization_id, artifact_uuid):
        """Retrieve the full content of a specific published artifact."""
        pass

    @abstractmethod
    def delete_chat(self, organization_id, conversation_uuids):
        """Delete specified chats for a given organization."""
        pass


class BaseClaudeAIProvider(BaseProvider):
    BASE_URL = "https://api.claude.ai/api"

    def __init__(self, session_key=None, session_key_expiry=None):
        self.session_key = session_key
        self.session_key_expiry = session_key_expiry
        self.logger = logging.getLogger(__name__)
        self._configure_logging()

    def _configure_logging(self):
        log_level = self.config.get("log_level", "INFO")
        logging.basicConfig(level=getattr(logging, log_level))
        self.logger.setLevel(getattr(logging, log_level))

    def login(self):
        click.echo("To obtain your session key, please follow these steps:")
        click.echo("1. Open your web browser and go to https://claude.ai")
        click.echo("2. Log in to your Claude account if you haven't already")
        click.echo("3. Once logged in, open your browser's developer tools:")
        click.echo("   - Chrome/Edge: Press F12 or Ctrl+Shift+I (Cmd+Option+I on Mac)")
        click.echo("   - Firefox: Press F12 or Ctrl+Shift+I (Cmd+Option+I on Mac)")
        click.echo("   - Safari: Enable developer tools in Preferences > Advanced, then press Cmd+Option+I")
        click.echo("4. In the developer tools, go to the 'Application' tab (Chrome/Edge) or 'Storage' tab (Firefox)")
        click.echo("5. In the left sidebar, expand 'Cookies' and select 'https://claude.ai'")
        click.echo("6. Locate the cookie named 'sessionKey' and copy its value. Ensure that the value is not URL-encoded.")

        while True:
            session_key = click.prompt("Please enter your sessionKey", type=str, hide_input=True)
            if not session_key.startswith("sk-ant"):
                click.echo("Invalid sessionKey format. Please make sure it starts with 'sk-ant'.")
                continue
            if is_url_encoded(session_key):
                click.echo("The session key appears to be URL-encoded. Please provide the decoded version.")
                continue

            expires = _get_session_key_expiry()
            self.session_key = session_key
            self.session_key_expiry = expires
            try:
                organizations = self.get_organizations()
                if organizations:
                    break  # Exit the loop if organizations are successfully retrieved
            except ProviderError as e:
                click.echo(e)
                click.echo("Failed to retrieve organizations. Please enter a valid sessionKey.")

        return self.session_key, self.session_key_expiry

    def get_organizations(self):
        url = urllib.parse.urljoin(self.BASE_URL, "/organizations")
        request = urllib.request.Request(url, headers={"Authorization": f"Bearer {self.session_key}"})
        try:
            response = urllib.request.urlopen(request)
            if response.getcode() != 200:
                raise ProviderError(f"HTTP error: {response.getcode()}")
            data = response.read()
            with gzip.GzipFile(fileobj=io.BytesIO(data)) as decompressed:
                organizations = json.loads(decompressed.read().decode('utf-8'))
            return [{"id": org['uuid'], "name": org['name']} for org in organizations if (set(org.get('capabilities', [])) & {'chat', 'claude_pro'} or set(org.get('capabilities', [])) & {'chat', 'raven'})]
        except urllib.error.HTTPError as e:
            raise ProviderError(f"HTTP error: {e.code}")
        except Exception as e:
            raise ProviderError(f"An error occurred: {str(e)}")

    def get_projects(self, organization_id, include_archived=False):
        url = urllib.parse.urljoin(self.BASE_URL, f"/organizations/{organization_id}/projects")
        request = urllib.request.Request(url, headers={"Authorization": f"Bearer {self.session_key}"})
        try:
            response = urllib.request.urlopen(request)
            if response.getcode() != 200:
                raise ProviderError(f"HTTP error: {response.getcode()}")
            data = response.read()
            with gzip.GzipFile(fileobj=io.BytesIO(data)) as decompressed:
                projects = json.loads(decompressed.read().decode('utf-8'))
            return [{"id": project['uuid'], "name": project['name'], "archived_at": project.get('archived_at')} for project in projects if include_archived or project.get('archived_at') is None]
        except urllib.error.HTTPError as e:
            raise ProviderError(f"HTTP error: {e.code}")
        except Exception as e:
            raise ProviderError(f"An error occurred: {str(e)}")

    def _make_request(self, method, endpoint, data=None):
        url = urllib.parse.urljoin(self.BASE_URL, endpoint)
        headers = {
            "Authorization": f"Bearer {self.session_key}",
            "Content-Type": "application/json"
        }
        request = urllib.request.Request(url, headers=headers)
        if data:
            request.data = json.dumps(data).encode('utf-8')
        try:
            response = urllib.request.urlopen(request)
            if response.getcode() != 200:
                raise ProviderError(f"HTTP error: {response.getcode()}")
            if response.headers.get("Content-Encoding") == "gzip":
                data = response.read()
                with gzip.GzipFile(fileobj=io.BytesIO(data)) as decompressed:
                    return json.loads(decompressed.read().decode('utf-8'))
            else:
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            raise ProviderError(f"HTTP error: {e.code}")
        except Exception as e:
            raise ProviderError(f"An error occurred: {str(e)}")
