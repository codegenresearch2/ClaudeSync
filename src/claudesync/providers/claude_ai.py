import json
import gzip
import urllib.request
import urllib.error
from .base_claude_ai import BaseClaudeAIProvider
from ..exceptions import ProviderError
import logging

class ClaudeAIProvider(BaseClaudeAIProvider):
    def _make_request(self, method, endpoint, data=None):
        url = f"{self.BASE_URL}{endpoint}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
        }

        if data:
            headers["Content-Type"] = "application/json"
            data = json.dumps(data).encode("utf-8")

        request = urllib.request.Request(url, method=method.upper(), headers=headers, data=data)

        try:
            with urllib.request.urlopen(request) as response:
                response_body = response.read()
                if response.info().get("Content-Encoding") == "gzip":
                    response_body = gzip.decompress(response_body)

                response_body = response_body.decode("utf-8")

                if response.status == 403:
                    error_msg = (
                        "Received a 403 Forbidden error. Your session key might be invalid. "
                        "Please try logging out and logging in again. If the issue persists, "
                        "you can try using the claude.ai-curl provider as a workaround:\n"
                        "claudesync api logout\n"
                        "claudesync api login claude.ai-curl"
                    )
                    self.logger.error(error_msg)
                    raise ProviderError(error_msg)

                try:
                    return json.loads(response_body)
                except json.JSONDecodeError as json_err:
                    self.logger.error(f"Failed to parse JSON response: {str(json_err)}")
                    self.logger.error(f"Response content: {response_body}")
                    raise ProviderError(f"Invalid JSON response from API: {str(json_err)}")

        except urllib.error.HTTPError as e:
            if e.status == 403:
                error_msg = (
                    "Received a 403 Forbidden error. Your session key might be invalid. "
                    "Please try logging out and logging in again. If the issue persists, "
                    "you can try using the claude.ai-curl provider as a workaround:\n"
                    "claudesync api logout\n"
                    "claudesync api login claude.ai-curl"
                )
                self.logger.error(error_msg)
                raise ProviderError(error_msg)
            else:
                self.logger.error(f"HTTP error occurred: {e.status}")
                raise ProviderError(f"HTTP error: {e.status}")

        except urllib.error.URLError as e:
            self.logger.error(f"URL error occurred: {e.reason}")
            raise ProviderError(f"URL error: {e.reason}")