import json
import urllib.request
import urllib.error
from .base_claude_ai import BaseClaudeAIProvider
from ..exceptions import ProviderError
import gzip
import io

class ClaudeAIProvider(BaseClaudeAIProvider):
    def _make_request(self, method, endpoint, data=None):
        url = f"{self.BASE_URL}{endpoint}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
            "Content-Type": "application/json",
            "Accept-Encoding": "gzip, deflate, zstd",
        }

        request = urllib.request.Request(url, method=method, headers=headers, data=json.dumps(data).encode("utf-8") if data else None)

        cookies = {
            "sessionKey": self.session_key,
            "CH-prefers-color-scheme": "dark",
            "anthropic-consent-preferences": '{"analytics":true,"marketing":true}',
        }

        for key, value in cookies.items():
            request.add_header(key, value)

        try:
            self.logger.debug(f"Making {method} request to {url}")
            with urllib.request.urlopen(request) as response:
                response_data = response.read()
                response_headers = dict(response.getheaders())

                self.logger.debug(f"Response status code: {response.status}")
                self.logger.debug(f"Response headers: {response_headers}")
                if len(response_data) > 1000:
                    self.logger.debug(f"Response content: {response_data[:1000]}...")
                else:
                    self.logger.debug(f"Response content: {response_data}")

                if response.status == 403:
                    error_msg = "403 Forbidden error: Your session key might be invalid. Please try logging out and logging in again. If the issue persists, you can try using the claude.ai-curl provider as a workaround:\nclaudesync api logout\nclaudesync api login claude.ai-curl"
                    self.logger.error(error_msg)
                    raise ProviderError(error_msg)

                if "Content-Encoding" in response_headers and response_headers["Content-Encoding"] == "gzip":
                    response_data = gzip.decompress(response_data)

                return json.loads(response_data.decode("utf-8"))

        except urllib.error.HTTPError as e:
            self.logger.error(f"HTTP Error {e.code}: {e.read().decode('utf-8')}")
            raise ProviderError(f"API request failed: {e.reason}")

        except urllib.error.URLError as e:
            self.logger.error(f"Request failed: {e.reason}")
            raise ProviderError(f"API request failed: {e.reason}")

    def _handle_http_error(self, status_code, response_content):
        if status_code == 403:
            error_msg = "403 Forbidden error: Your session key might be invalid. Please try logging out and logging in again. If the issue persists, you can try using the claude.ai-curl provider as a workaround:\nclaudesync api logout\nclaudesync api login claude.ai-curl"
            self.logger.error(error_msg)
            raise ProviderError(error_msg)
        elif status_code == 400:
            error_msg = f"Bad Request: The server cannot or will not process the request due to something that is perceived to be a client error. Response content: {response_content}"
            self.logger.error(error_msg)
            raise ProviderError(error_msg)
        elif status_code == 500:
            error_msg = f"Internal Server Error: The server encountered an unexpected condition that prevented it from fulfilling the request. Response content: {response_content}"
            self.logger.error(error_msg)
            raise ProviderError(error_msg)
        else:
            error_msg = f"HTTP Error {status_code}: {response_content}"
            self.logger.error(error_msg)
            raise ProviderError(error_msg)