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

        cookies = {
            "sessionKey": self.session_key,
            "CH-prefers-color-scheme": "dark",
            "anthropic-consent-preferences": '{"analytics":true,"marketing":true}',
        }

        request = urllib.request.Request(url, headers=headers)
        for key, value in cookies.items():
            request.add_header(key, value)

        try:
            self.logger.debug(f"Making {method} request to {url}")
            self.logger.debug(f"Headers: {headers}")
            self.logger.debug(f"Cookies: {cookies}")
            if data:
                self.logger.debug(f"Request data: {data}")

            response = urllib.request.urlopen(request)
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

            try:
                return json.loads(response_data.decode("utf-8"))
            except json.JSONDecodeError as json_err:
                self.logger.error(f"Failed to parse JSON response: {str(json_err)}")
                self.logger.error(f"Response content: {response_data.decode('utf-8')}")
                raise ProviderError(f"Invalid JSON response from API: {str(json_err)}")

        except urllib.error.URLError as e:
            self.logger.error(f"Request failed: {str(e)}")
            raise ProviderError(f"API request failed: {str(e)}")

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