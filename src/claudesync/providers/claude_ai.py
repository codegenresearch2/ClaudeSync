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
            "Cookie": f"sessionKey={self.session_key}; CH-prefers-color-scheme=dark; anthropic-consent-preferences={json.dumps({'analytics':True,'marketing':True})}",
        }

        try:
            self.logger.debug(f"Making {method} request to {url}")
            self.logger.debug(f"Headers: {headers}")
            if data:
                self.logger.debug(f"Request data: {data}")
                data = json.dumps(data).encode('utf-8')

            req = urllib.request.Request(url, data=data, headers=headers, method=method)
            with urllib.request.urlopen(req) as response:
                self.logger.debug(f"Response status code: {response.status}")
                self.logger.debug(f"Response headers: {response.headers}")

                if response.info().get('Content-Encoding') == 'gzip':
                    response_content = gzip.decompress(response.read()).decode('utf-8')
                else:
                    response_content = response.read().decode('utf-8')

                self.logger.debug(f"Response content: {response_content[:1000]}...")

                if response.status == 403:
                    error_msg = "Received a 403 Forbidden error. Your session key might be invalid. Please try logging out and logging in again. If the issue persists, you can try using the claude.ai-curl provider as a workaround:\nclaudesync api logout\nclaudesync api login claude.ai-curl"
                    self.logger.error(error_msg)
                    raise ProviderError(error_msg)

                if not response_content:
                    return None

                return json.loads(response_content)

        except urllib.error.URLError as e:
            self.logger.error(f"Request failed: {str(e.reason)}")
            raise ProviderError(f"API request failed: {str(e.reason)}")
        except json.JSONDecodeError as json_err:
            self.logger.error(f"Failed to parse JSON response: {str(json_err)}")
            self.logger.error(f"Response content: {response_content}")
            raise ProviderError(f"Invalid JSON response from API: {str(json_err)}")