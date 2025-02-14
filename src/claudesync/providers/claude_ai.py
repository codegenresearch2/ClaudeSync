import json
import urllib.request
import urllib.error
from .base_claude_ai import BaseClaudeAIProvider
from ..exceptions import ProviderError


class ClaudeAIProvider(BaseClaudeAIProvider):
    def _make_request(self, method, endpoint, data=None):
        url = f"{self.BASE_URL}{endpoint}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
            "Origin": "https://claude.ai",
            "Referer": "https://claude.ai/projects",
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, zstd",
            "Accept-Language": "en-US,en;q=0.5",
            "anthropic-client-sha": "unknown",
            "anthropic-client-version": "unknown",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        }

        cookies = {
            "sessionKey": self.session_key,
            "CH-prefers-color-scheme": "dark",
            "anthropic-consent-preferences": '{"analytics":true,"marketing":true}',
        }

        request = urllib.request.Request(url, headers=headers, method=method)
        for key, value in cookies.items():
            request.add_header(key, value)
        if data:
            json_data = json.dumps(data).encode("utf-8")
            request.add_header("Content-Type", "application/json")
            request.add_header("Content-Length", len(json_data))
            request.data = json_data

        try:
            self.logger.debug(f"Making {method} request to {url}")
            self.logger.debug(f"Headers: {headers}")
            self.logger.debug(f"Cookies: {cookies}")
            if data:
                self.logger.debug(f"Request data: {data}")

            with urllib.request.urlopen(request) as response:
                response_body = response.read()
                response_headers = dict(response.getheaders())

                self.logger.debug(f"Response status code: {response.status}")
                self.logger.debug(f"Response headers: {response_headers}")
                self.logger.debug(f"Response content: {response_body[:1000]}...")

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

                if not response_body:
                    return None

                return json.loads(response_body)

        except urllib.error.HTTPError as e:
            self.logger.error(f"Request failed: {str(e)}")
            self.logger.error(f"Response status code: {e.code}")
            self.logger.error(f"Response headers: {e.headers}")
            self.logger.error(f"Response content: {e.read().decode('utf-8')}")
            raise ProviderError(f"API request failed: {str(e)}")
        except json.JSONDecodeError as json_err:
            self.logger.error(f"Failed to parse JSON response: {str(json_err)}")
            self.logger.error(f"Response content: {response_body.decode('utf-8')}")
            raise ProviderError(f"Invalid JSON response from API: {str(json_err)}")