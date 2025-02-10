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

        cookies = {
            "sessionKey": self.session_key,
        }

        try:
            self.logger.debug(f"Making {method} request to {url}")
            self.logger.debug(f"Headers: {headers}")
            self.logger.debug(f"Cookies: {cookies}")
            if data:
                self.logger.debug(f"Request data: {data}")
                data = json.dumps(data).encode("utf-8")

            req = urllib.request.Request(url, method=method)
            for key, value in headers.items():
                req.add_header(key, value)
            req.add_header("Cookie", "; ".join([f"{k}={v}" for k, v in cookies.items()]))
            if data:
                req.data = data

            with urllib.request.urlopen(req) as response:
                self.logger.debug(f"Response status code: {response.status}")
                self.logger.debug(f"Response headers: {response.headers}")

                if response.headers.get("Content-Encoding") == "gzip":
                    content = gzip.decompress(response.read())
                else:
                    content = response.read()

                content_str = content.decode("utf-8")
                self.logger.debug(f"Response content: {content_str[:1000]}...")

                self._handle_http_error(response.status, content_str)

                if not content_str:
                    return None

                return json.loads(content_str)

        except urllib.error.URLError as e:
            self.logger.error(f"Request failed: {str(e)}")
            if hasattr(e, "code"):
                self.logger.error(f"Response status code: {e.code}")
            if hasattr(e, "headers"):
                self.logger.error(f"Response headers: {e.headers}")
            if hasattr(e, "read"):
                self.logger.error(f"Response content: {e.read().decode('utf-8')}")
            raise ProviderError(f"API request failed: {str(e)}")
        except json.JSONDecodeError as json_err:
            self.logger.error(f"Failed to parse JSON response: {str(json_err)}")
            self.logger.error(f"Response content: {content_str}")
            raise ProviderError(f"Invalid JSON response from API: {str(json_err)}")

    def _handle_http_error(self, status_code, content):
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