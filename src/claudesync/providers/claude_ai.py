import json
import urllib.request
import gzip
from .base_claude_ai import BaseClaudeAIProvider
from ..exceptions import ProviderError

class ClaudeAIProvider(BaseClaudeAIProvider):
    def _make_request(self, method, endpoint, data=None):
        url = f"{self.BASE_URL}{endpoint}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
            "Content-Type": "application/json",
            "Accept-Encoding": "gzip, deflate, zstd",
        }

        cookies = {
            "sessionKey": self.session_key,
        }

        request = urllib.request.Request(url, headers=headers, method=method)

        try:
            self.logger.debug(f"Making {method} request to {url}")
            self.logger.debug(f"Headers: {headers}")
            self.logger.debug(f"Cookies: {cookies}")
            if data:
                self.logger.debug(f"Request data: {data}")

            with urllib.request.urlopen(request) as response:
                response_content = response.read()
                if response.info().get("Content-Encoding") == "gzip":
                    response_content = gzip.decompress(response_content)
                self.logger.debug(f"Response content: {response_content[:1000]}...")

                if response.status == 403:
                    error_msg = (
                        "Received a 403 Forbidden error. Your session key might be invalid. "
                        "Please try logging out and logging in again. If the issue persists, "
                        "you can try using the claude.ai-curl provider as a workaround:"
                        "claudesync api logout\n"
                        "claudesync api login claude.ai-curl"
                    )
                    self.logger.error(error_msg)
                    raise ProviderError(error_msg)

                response.raise_for_status()

                if not response_content:
                    return None

                return json.loads(response_content.decode('utf-8'))

        except urllib.error.HTTPError as e:
            self.logger.error(f"HTTP error occurred: {e.code} - {e.reason}")
            self.logger.error(f"Response headers: {e.headers}")
            raise ProviderError(f"HTTP error: {e.code} - {e.reason}")
        except urllib.error.URLError as e:
            self.logger.error(f"URL error occurred: {e.reason}")
            raise ProviderError(f"URL error: {e.reason}")
        except json.JSONDecodeError as json_err:
            self.logger.error(f"Failed to parse JSON response: {str(json_err)}")
            self.logger.error(f"Response content: {response_content}")
            raise ProviderError(f"Invalid JSON response from API: {str(json_err)}")
