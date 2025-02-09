import datetime
import logging
import urllib.request
import urllib.parse
import contextlib
import json

import click
from .base_provider import BaseProvider
from ..config_manager import ConfigManager
from ..exceptions import ProviderError


def is_url_encoded(s):
    decoded_s = urllib.parse.unquote(s)
    return decoded_s != s


def _get_session_key_expiry():
    date_format = "%a, %d %b %Y %H:%M:%S %Z"
    default_expires = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=30)
    formatted_expires = default_expires.strftime(date_format).strip()
    while True:
        expires = click.prompt(
            "Please enter the expires time for the sessionKey (optional)",
            default=formatted_expires,
            type=str,
        ).strip()
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
            session_key = click.prompt("Please enter your sessionKey", type=str, hide_input=True)
            if not session_key.startswith("sk-ant"):
                click.echo("Invalid sessionKey format. Please make sure it starts with 'sk-ant'.")
                continue
            if is_url_encoded(session_key):
                click.echo("The session key appears to be URL-encoded. Please provide the decoded version.")
                continue

            self.session_key = session_key
            self.session_key_expiry = _get_session_key_expiry()

            try:
                organizations = self.get_organizations()
                if organizations:
                    return self.session_key, self.session_key_expiry
            except ProviderError as e:
                click.echo(e)
                continue

    def get_organizations(self):
        url = f"{self.BASE_URL}/organizations"
        req = urllib.request.Request(url, method="GET")
        req.add_header("Authorization", self.session_key)
        with contextlib.closing(urllib.request.urlopen(req)) as response:
            response_data = response.read()
            organizations = json.loads(response_data)
        if not organizations:
            raise ProviderError("Unable to retrieve organization information")
        return [{"id": org['uuid'], "name": org['name']} for org in organizations if (set(org.get('capabilities', [])) & {"chat", "claude_pro"} or set(org.get('capabilities', [])) & {"chat", "raven"})]

    def get_projects(self, organization_id, include_archived=False):
        endpoint = f"{self.BASE_URL}/organizations/{organization_id}/projects"
        req = urllib.request.Request(endpoint, method="GET")
        req.add_header("Authorization", self.session_key)
        with contextlib.closing(urllib.request.urlopen(req)) as response:
            response_data = response.read()
            projects = json.loads(response_data)
        return [{"id": project['uuid'], "name": project['name'], "archived_at": project.get('archived_at')} for project in projects if include_archived or project.get('archived_at') is None]

    def _make_request(self, method, endpoint, data=None):
        url = f"{self.BASE_URL}{endpoint}"
        req = urllib.request.Request(url, method=method)
        if data:
            req.data = data
        req.add_header("Authorization", self.session_key)
        try:
            with contextlib.closing(urllib.request.urlopen(req)) as response:
                response_data = response.read()
                return json.loads(response_data)
        except urllib.error.HTTPError as e:
            raise ProviderError(f"HTTP Error: {e.code} - {e.reason}")

    def list_files(self, organization_id, project_id):
        endpoint = f"{self.BASE_URL}/organizations/{organization_id}/projects/{project_id}/docs"
        req = urllib.request.Request(endpoint, method="GET")
        req.add_header("Authorization", self.session_key)
        with contextlib.closing(urllib.request.urlopen(req)) as response:
            response_data = response.read()
            files = json.loads(response_data)
        return [{"uuid": file['uuid'], "file_name": file['file_name'], "content": file['content'], "created_at": file['created_at']} for file in files]

    def upload_file(self, organization_id, project_id, file_name, content):
        endpoint = f"{self.BASE_URL}/organizations/{organization_id}/projects/{project_id}/docs"
        data = {"file_name": file_name, "content": content}
        req = urllib.request.Request(endpoint, data=json.dumps(data).encode('utf-8'), method="POST")
        req.add_header("Authorization", self.session_key)
        with contextlib.closing(urllib.request.urlopen(req)) as response:
            response_data = response.read()
            return json.loads(response_data)

    def delete_file(self, organization_id, project_id, file_uuid):
        endpoint = f"{self.BASE_URL}/organizations/{organization_id}/projects/{project_id}/docs/{file_uuid}"
        req = urllib.request.Request(endpoint, method="DELETE")
        req.add_header("Authorization", self.session_key)
        with contextlib.closing(urllib.request.urlopen(req)) as response:
            response_data = response.read()
            return json.loads(response_data)

    def archive_project(self, organization_id, project_id):
        endpoint = f"{self.BASE_URL}/organizations/{organization_id}/projects/{project_id}"
        data = {"is_archived": True}
        req = urllib.request.Request(endpoint, data=json.dumps(data).encode('utf-8'), method="PUT")
        req.add_header("Authorization", self.session_key)
        with contextlib.closing(urllib.request.urlopen(req)) as response:
            response_data = response.read()
            return json.loads(response_data)

    def create_project(self, organization_id, name, description=""):
        endpoint = f"{self.BASE_URL}/organizations/{organization_id}/projects"
        data = {"name": name, "description": description, "is_private": True}
        req = urllib.request.Request(endpoint, data=json.dumps(data).encode('utf-8'), method="POST")
        req.add_header("Authorization", self.session_key)
        with contextlib.closing(urllib.request.urlopen(req)) as response:
            response_data = response.read()
            return json.loads(response_data)

    def get_chat_conversations(self, organization_id):
        endpoint = f"{self.BASE_URL}/organizations/{organization_id}/chat_conversations"
        req = urllib.request.Request(endpoint, method="GET")
        req.add_header("Authorization", self.session_key)
        with contextlib.closing(urllib.request.urlopen(req)) as response:
            response_data = response.read()
            return json.loads(response_data)

    def get_published_artifacts(self, organization_id):
        endpoint = f"{self.BASE_URL}/organizations/{organization_id}/published_artifacts"
        req = urllib.request.Request(endpoint, method="GET")
        req.add_header("Authorization", self.session_key)
        with contextlib.closing(urllib.request.urlopen(req)) as response:
            response_data = response.read()
            return json.loads(response_data)

    def get_chat_conversation(self, organization_id, conversation_id):
        endpoint = f"{self.BASE_URL}/organizations/{organization_id}/chat_conversations/{conversation_id}?rendering_mode=raw"
        req = urllib.request.Request(endpoint, method="GET")
        req.add_header("Authorization", self.session_key)
        with contextlib.closing(urllib.request.urlopen(req)) as response:
            response_data = response.read()
            return json.loads(response_data)

    def get_artifact_content(self, organization_id, artifact_uuid):
        endpoint = f"{self.BASE_URL}/organizations/{organization_id}/published_artifacts"
        req = urllib.request.Request(endpoint, method="GET")
        req.add_header("Authorization", self.session_key)
        with contextlib.closing(urllib.request.urlopen(req)) as response:
            response_data = response.read()
            artifacts = json.loads(response_data)
        for artifact in artifacts:
            if artifact["published_artifact_uuid"] == artifact_uuid:
                return artifact.get("artifact_content", "")
        raise ProviderError(f"Artifact with UUID {artifact_uuid} not found")

    def delete_chat(self, organization_id, conversation_uuids):
        endpoint = f"{self.BASE_URL}/organizations/{organization_id}/chat_conversations/delete_many"
        data = {"conversation_uuids": conversation_uuids}
        req = urllib.request.Request(endpoint, data=json.dumps(data).encode('utf-8'), method="POST")
        req.add_header("Authorization", self.session_key)
        with contextlib.closing(urllib.request.urlopen(req)) as response:
            response_data = response.read()
            return json.loads(response_data)
