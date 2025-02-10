import json
import urllib.request
import urllib.error
from .base_claude_ai import BaseClaudeAIProvider
from ..exceptions import ProviderError
import logging
import gzip

class ClaudeAIProvider(BaseClaudeAIProvider):
    def _make_request(self, method, endpoint, data=None):
        url = f"{self.BASE_URL}{endpoint}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
            "Content-Type": "application/json",
            "Accept-Encoding": "gzip, deflate"
        }

        if self.session_key:
            headers["Cookie"] = f"sessionKey={self.session_key}"

        request = urllib.request.Request(url, method=method.upper(), headers=headers)

        if data:
            json_data = json.dumps(data).encode("utf-8")
            request.add_header("Content-Length", len(json_data))
            urllib.request.urlopen(request, json_data)

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
                    logging.error(error_msg)
                    raise ProviderError(error_msg)

                try:
                    return json.loads(response_body)
                except json.JSONDecodeError as json_err:
                    logging.error(f"Failed to parse JSON response: {str(json_err)}")
                    logging.error(f"Response content: {response_body}")
                    raise ProviderError(f"Invalid JSON response from API: {str(json_err)}")

        except urllib.error.HTTPError as e:
            logging.error(f"HTTP error occurred: {e.code} {e.reason}")
            raise ProviderError(f"API request failed: {str(e)}")
        except urllib.error.URLError as e:
            logging.error(f"URL error occurred: {e.reason}")
            raise ProviderError(f"API request failed: {str(e)}")
        except UnicodeDecodeError as e:
            logging.error(f"Unicode decode error occurred: {str(e)}")
            raise ProviderError(f"Unicode decode error: {str(e)}")