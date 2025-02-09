import json
import urllib.request
import urllib.error
from .base_claude_ai import BaseClaudeAIProvider
from ..exceptions import ProviderError
import gzip

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
                response_headers = dict(response.getheaders())
                response_data = response.read()

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

                try:
                    return json.loads(response_data.decode("utf-8"))
                except json.JSONDecodeError as e:
                    self.logger.error(f"Failed to parse JSON response: {str(e)}")
                    raise ProviderError(f"Invalid JSON response from API: {str(e)}")

        except urllib.error.HTTPError as e:
            if e.code == 403:
                error_msg = "403 Forbidden error: Your session key might be invalid. Please try logging out and logging in again. If the issue persists, you can try using the claude.ai-curl provider as a workaround:\nclaudesync api logout\nclaudesync api login claude.ai-curl"
                self.logger.error(error_msg)
                raise ProviderError(error_msg)
            else:
                self.logger.error(f"HTTP Error {e.code}: {e.read().decode('utf-8')}")
                raise ProviderError(f"API request failed: {e.reason}")

        except urllib.error.URLError as e:
            self.logger.error(f"Request failed: {e.reason}")
            raise ProviderError(f"API request failed: {e.reason}")