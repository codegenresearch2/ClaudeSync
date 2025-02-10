import json
import urllib.request
import urllib.error
import urllib.parse
import gzip
from .base_claude_ai import BaseClaudeAIProvider
from ..exceptions import ProviderError

class ClaudeAIProvider(BaseClaudeAIProvider):
    def _make_request(self, method, endpoint, data=None):
        url = f"{self.BASE_URL}{endpoint}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
            "Content-Type": "application/json",
            "Accept-Encoding": "gzip",
        }

        try:
            self.logger.debug(f"Making {method} request to {url}")
            self.logger.debug(f"Headers: {headers}")
            self.logger.debug(f"Cookies: sessionKey={self.session_key}")
            if data:
                data = json.dumps(data).encode("utf-8")
                self.logger.debug(f"Request data: {data}")

            req = urllib.request.Request(url, data=data, headers=headers)
            req.add_header("Cookie", f"sessionKey={self.session_key}")

            with urllib.request.urlopen(req) as response:
                self.logger.debug(f"Response status code: {response.status}")
                self.logger.debug(f"Response headers: {response.headers}")

                if response.headers.get("Content-Encoding") == "gzip":
                    content = gzip.decompress(response.read())
                else:
                    content = response.read()

                content_str = content.decode("utf-8")
                self.logger.debug(f"Response content: {content_str[:1000]}...")

                self.handle_http_error(response)

                if not content:
                    return None

                return json.loads(content_str)

        except urllib.error.HTTPError as e:
            self.handle_http_error(e)
        except urllib.error.URLError as e:
            self.logger.error(f"Request failed: {str(e)}")
            raise ProviderError(f"API request failed: URL error - {str(e)}")
        except json.JSONDecodeError as json_err:
            self.logger.error(f"Failed to parse JSON response: {str(json_err)}")
            self.logger.error(f"Response content: {content_str}")
            raise ProviderError(f"Invalid JSON response from API: {str(json_err)}")

    def handle_http_error(self, e):
        if isinstance(e, urllib.error.HTTPError):
            status_code = e.code
            content = e.read().decode("utf-8")
        else:
            status_code = e.status
            content = e.read().decode("utf-8")

        if status_code == 403:
            error_msg = (
                "Received a 403 Forbidden error. Your session key might be invalid. "
                "Please try logging out and logging in again. If the issue persists, "
                "you can try using the claude.ai-curl provider as a workaround:\n"
                "claudesync api logout\n"
                "claudesync api login claude.ai-curl"
            )
            self.logger.error(error_msg)
            raise ProviderError(f"API request failed: 403 Forbidden error - {error_msg}")
        elif status_code >= 400:
            error_msg = f"API request failed: {status_code} - {content}"
            self.logger.error(error_msg)
            raise ProviderError(error_msg)