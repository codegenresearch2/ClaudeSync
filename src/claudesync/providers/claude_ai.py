import json
import urllib.request
import urllib.parse
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

        if data:
            headers["Content-Type"] = "application/json"

        request = urllib.request.Request(url, method=method.upper(), headers=headers)
        for key, value in request.headers.items():
            if key.lower() == "cookie":
                request.add_header(key, value)
            elif key.lower() != "content-length" and key.lower() != "content-type":
                request.add_header(key, value)

        try:
            with urllib.request.urlopen(request) as response:
                response_body = response.read()
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

                if response.info().get("Content-Encoding") == "gzip":
                    import gzip
                    response_body = gzip.decompress(response_body)

                response_body = response_body.decode("utf-8")

                try:
                    return json.loads(response_body)
                except json.JSONDecodeError as json_err:
                    self.logger.error(f"Failed to parse JSON response: {str(json_err)}")
                    self.logger.error(f"Response content: {response_body}")
                    raise ProviderError(f"Invalid JSON response from API: {str(json_err)}")

        except urllib.error.HTTPError as e:
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
            else:
                self.logger.error(f"Request failed: {str(e)}")
                raise ProviderError(f"API request failed: {str(e)}")
        except urllib.error.URLError as e:
            self.logger.error(f"Request failed: {str(e)}")
            raise ProviderError(f"API request failed: {str(e)}")
        except json.JSONDecodeError as json_err:
            self.logger.error(f"Failed to parse JSON response: {str(json_err)}")
            raise ProviderError(f"Invalid JSON response from API: {str(json_err)}")