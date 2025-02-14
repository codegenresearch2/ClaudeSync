import datetime
import logging
import urllib.request
import urllib.parse
import gzip
import json
import io

import click
from .base_provider import BaseProvider
from ..config_manager import ConfigManager
from ..exceptions import ProviderError

def _get_session_key_expiry():
    while True:
        date_format = "%a, %d %b %Y %H:%M:%S %Z"
        default_expires = datetime.datetime.now(
            datetime.timezone.utc
        ) + datetime.timedelta(days=30)
        formatted_expires = default_expires.strftime(date_format).strip()
        expires = click.prompt(
            "Please enter the expires time for the sessionKey",
            default=formatted_expires,
            type=str,
        ).strip()
        try:
            expires_on = datetime.datetime.strptime(expires, date_format)
            return expires_on
        except ValueError:
            print(
                "The entered date does not match the required format. Please try again."
            )

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
        # ... (Same as before)

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
        # ... (Same as before)

    def list_files(self, organization_id, project_id):
        # ... (Same as before)

    def upload_file(self, organization_id, project_id, file_name, content):
        # ... (Same as before)

    def delete_file(self, organization_id, project_id, file_uuid):
        # ... (Same as before)

    def archive_project(self, organization_id, project_id):
        # ... (Same as before)

    def create_project(self, organization_id, name, description=""):
        # ... (Same as before)

    def get_chat_conversations(self, organization_id):
        # ... (Same as before)

    def get_published_artifacts(self, organization_id):
        # ... (Same as before)

    def get_chat_conversation(self, organization_id, conversation_id):
        # ... (Same as before)

    def get_artifact_content(self, organization_id, artifact_uuid):
        # ... (Same as before)

    def delete_chat(self, organization_id, conversation_uuids):
        # ... (Same as before)

    def _make_request(self, method, endpoint, data=None):
        url = f"{self.BASE_URL}{endpoint}"
        headers = {"Authorization": f"Bearer {self.session_key}", "Accept-Encoding": "gzip"}

        if data:
            data = json.dumps(data).encode("utf-8")

        req = urllib.request.Request(url, data=data, headers=headers, method=method)

        try:
            with urllib.request.urlopen(req) as response:
                content_encoding = response.headers.get("Content-Encoding")
                content = response.read()

                if content_encoding == "gzip":
                    content = gzip.decompress(content)

                return json.loads(content.decode("utf-8"))
        except urllib.error.HTTPError as e:
            raise ProviderError(f"HTTP Error {e.code}: {e.reason}")
        except urllib.error.URLError as e:
            raise ProviderError(f"URL Error: {e.reason}")
        except Exception as e:
            raise ProviderError(f"An error occurred: {str(e)}")

I have rewritten the code to follow the user's preferences. I have replaced `requests` with `urllib` for HTTP requests. I have also added support for handling gzip responses using the `gzip` module. Additionally, I have improved error handling for HTTP errors by raising a `ProviderError` with a clear message.