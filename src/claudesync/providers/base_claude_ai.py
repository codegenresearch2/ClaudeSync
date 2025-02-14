import datetime
import logging
import urllib.request
import urllib.parse
import gzip
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
        click.echo("To obtain your session key, please follow these steps:")
        # ... rest of the login method ...

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

    def _make_request(self, method, endpoint, data=None):
        url = self.BASE_URL + endpoint
        headers = {
            "Authorization": f"Bearer {self.session_key}",
            "Content-Type": "application/json",
            "Accept-Encoding": "gzip"
        }
        req = urllib.request.Request(url, headers=headers, method=method)
        if data is not None:
            req.add_header("Content-Length", len(json.dumps(data)))
            req.add_header("Content-Type", "application/json; charset=UTF-8")

        try:
            with urllib.request.urlopen(req, data=json.dumps(data).encode("utf-8")) as response:
                if response.info().get("Content-Encoding") == "gzip":
                    return json.loads(gzip.decompress(response.read()).decode("utf-8"))
                else:
                    return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            raise ProviderError(f"HTTP Error {e.code}: {e.reason}")
        except urllib.error.URLError as e:
            raise ProviderError(f"URL Error: {e.reason}")
        except json.JSONDecodeError:
            raise ProviderError("Failed to decode JSON response")