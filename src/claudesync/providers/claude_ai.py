import urllib.request
import urllib.error
import json
import gzip
from datetime import datetime, timezone

from .base_claude_ai import BaseClaudeAIProvider
from ..exceptions import ProviderError


class ClaudeAIProvider(BaseClaudeAIProvider):
    def _make_request(self, method, endpoint, data=None):
        url = f"{self.BASE_URL}{endpoint}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:129.0) Gecko/20100101 Firefox/129.0",
            "Content-Type": "application/json",
        }

        # Add session key to headers if available
        if self.session_key:
            headers["Cookie"] = f"sessionKey={self.session_key}"

        try:
            self.logger.debug(f"Making {method} request to {url}")
            self.logger.debug(f"Headers: {headers}")
            if data:
                self.logger.debug(f"Request data: {data}")

            req = urllib.request.Request(url, method=method, headers=headers)
            if data:
                json_data = json.dumps(data).encode("utf-8")
                req.data = json_data

            with urllib.request.urlopen(req) as response:
                content_encoding = response.headers.get("Content-Encoding", "")
                content = response.read()

                if content_encoding == "gzip":
                    content = gzip.decompress(content)

                content_str = content.decode("utf-8")
                self.logger.debug(f"Response content: {content_str[:1000]}...")

                if not content_str:
                    return None

                try:
                    return json.loads(content_str)
                except json.JSONDecodeError as json_err:
                    error_message = (
                        f"Failed to parse JSON response: {content_str}. Reason: {json_err}. Request headers: {headers}"
                    )
                    self.logger.error(error_message)
                    raise ProviderError(error_message)

        except urllib.error.HTTPError as e:
            self.handle_http_error(e)
        except urllib.error.URLError as e:
            self.logger.error(f"URL Error: {str(e)}")
            raise ProviderError(f"API request failed: {str(e)}")
        except json.JSONDecodeError as json_err:
            self.logger.error(f"Failed to parse JSON response: {json_err}")
            raise ProviderError(f"Invalid JSON response from API: {json_err}")

    def handle_http_error(self, e):
        try:
            response_content = e.read().decode("utf-8")
        except UnicodeDecodeError:
            response_content = e.read().decode("iso-8859-1")

        self.logger.debug(f"Request failed: {str(e)}")
        self.logger.debug(f"Response status code: {e.code}")
        self.logger.debug(f"Response headers: {e.headers}")
        self.logger.debug(f"Response content: {response_content}")

        if e.code == 403:
            error_msg = (
                "Received a 403 Forbidden error. Your session key might be invalid. "
                "Please try logging out and logging in again. If the issue persists, "
                "you can try using the claude.ai-curl provider as a workaround:\n"
                "claudesync api logout\n"
                "claudesync api login claude.ai-curl"
            )
            self.logger.error(error_msg)
            raise ProviderError(error_msg)
        elif e.code == 429:
            try:
                error_data = json.loads(response_content)
                resets_at_unix = json.loads(error_data["error"]["message"])["resetsAt"]
                resets_at_local = datetime.fromtimestamp(
                    resets_at_unix, tz=timezone.utc
                ).astimezone()
                formatted_time = resets_at_local.strftime("%a %b %d %Y %H:%M:%S %Z%z")
                print(f"Message limit exceeded. Try again after {formatted_time}")
            except (KeyError, json.JSONDecodeError) as parse_error:
                print(f"Failed to parse error response: {parse_error}")
            raise ProviderError("HTTP 429: Too Many Requests")
        else:
            error_message = (
                f"API request failed with status code {e.code}. "
                f"Response content: {response_content}. Request headers: {headers}"
            )
            self.logger.error(error_message)
            raise ProviderError(error_message)

    def _make_request_stream(self, method, endpoint, data=None):
        url = f"{self.BASE_URL}{endpoint}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:129.0) Gecko/20100101 Firefox/129.0",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            "Cookie": f"sessionKey={self.session_key}",
        }

        req = urllib.request.Request(url, method=method, headers=headers)
        if data:
            req.data = json.dumps(data).encode("utf-8")

        try:
            return urllib.request.urlopen(req)
        except urllib.error.HTTPError as e:
            self.handle_http_error(e)
        except urllib.error.URLError as e:
            raise ProviderError(f"API request failed: {str(e)}")


This revised code snippet addresses the feedback from the oracle by improving the management of headers, cookies, and response handling. It also ensures consistent logging and error handling.