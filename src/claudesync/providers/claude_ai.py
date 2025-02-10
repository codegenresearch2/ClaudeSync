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

        cookies = {
            "sessionKey": self.session_key,
            "CH-prefers-color-scheme": "dark",
            "anthropic-consent-preferences": '{"analytics":true,"marketing":true}',
        }

        request = urllib.request.Request(url, method=method.upper())
        for key, value in headers.items():
            request.add_header(key, value)
        for key, value in cookies.items():
            request.add_header(key, value)

        if data:
            json_data = json.dumps(data).encode("utf-8")
            request.add_header("Content-Type", "application/json")
            request.add_header("Content-Length", len(json_data))
            urllib.request.urlopen(request, json_data)
        else:
            urllib.request.urlopen(request)

        response = urllib.request.urlopen(request)

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

        response_body = response.read().decode("utf-8")

        try:
            return json.loads(response_body)
        except json.JSONDecodeError as json_err:
            self.logger.error(f"Failed to parse JSON response: {str(json_err)}")
            self.logger.error(f"Response content: {response_body}")
            raise ProviderError(f"Invalid JSON response from API: {str(json_err)}")