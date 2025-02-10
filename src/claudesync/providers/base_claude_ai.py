import datetime
import logging
import urllib.request
import urllib.parse
import json

import click
from .base_provider import BaseProvider
from ..config_manager import ConfigManager
from ..exceptions import ProviderError

def is_url_encoded(s):
    decoded_s = urllib.parse.unquote(s)
    return decoded_s != s

def _get_session_key_expiry():
    while True:
        date_format = "%a, %d %b %Y %H:%M:%S %Z"
        default_expires = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=30)
        formatted_expires = default_expires.strftime(date_format).strip()
        expires = click.prompt("Please enter the expires time for the sessionKey (optional)", default=formatted_expires, type=str).strip()
        try:
            expires_on = datetime.datetime.strptime(expires, date_format)
            return expires_on
        except ValueError:
            print("The entered date does not match the required format. Please try again.")

class BaseClaudeAIProvider(BaseProvider):
    BASE_URL = "https://api.claude.ai/api"

    def __init__(self, session_key=None, session_key_expiry=None):
        self.config = ConfigManager()
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
            session_key = click.prompt("Please enter your sessionKey", type=str)
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
                    break  # Exit the loop if get_organizations is successful
            except ProviderError as e:
                click.echo(e)
                click.echo("Failed to retrieve organizations. Please enter a valid sessionKey.")

        return self.session_key, self.session_key_expiry

    def get_organizations(self):
        response = self._make_request("GET", "/organizations")
        if not response:
            raise ProviderError("Unable to retrieve organization information")
        return [
            {"id": org["uuid"], "name": org["name"]}
            for org in response
            if ({"chat", "claude_pro"}.issubset(set(org.get("capabilities", []))) or
                {"chat", "raven"}.issubset(set(org.get("capabilities", []))))
        ]

    def get_projects(self, organization_id, include_archived=False):
        # Implementation of get_projects method
        pass

    def list_files(self, organization_id, project_id):
        # Implementation of list_files method
        pass

    def upload_file(self, organization_id, project_id, file_name, content):
        # Implementation of upload_file method
        pass

    def delete_file(self, organization_id, project_id, file_uuid):
        # Implementation of delete_file method
        pass

    def archive_project(self, organization_id, project_id):
        # Implementation of archive_project method
        pass

    def create_project(self, organization_id, name, description=""):
        # Implementation of create_project method
        pass

    def get_chat_conversations(self, organization_id):
        # Implementation of get_chat_conversations method
        pass

    def get_published_artifacts(self, organization_id):
        # Implementation of get_published_artifacts method
        pass

    def get_chat_conversation(self, organization_id, conversation_id):
        # Implementation of get_chat_conversation method
        pass

    def get_artifact_content(self, organization_id, artifact_uuid):
        # Implementation of get_artifact_content method
        pass

    def delete_chat(self, organization_id, conversation_uuids):
        # Implementation of delete_chat method
        pass

    def _make_request(self, method, endpoint, data=None):
        url = f"{self.BASE_URL}{endpoint}"
        headers = {"Authorization": f"Bearer {self.session_key}", "Accept-Encoding": "gzip"}

        if data:
            data = json.dumps(data).encode("utf-8")

        req = urllib.request.Request(url, data=data, headers=headers, method=method)

        try:
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            raise ProviderError(f"HTTP Error {e.code}: {e.reason}")
        except urllib.error.URLError as e:
            raise ProviderError(f"URL Error: {e.reason}")
        except json.JSONDecodeError:
            raise ProviderError("Invalid JSON response")