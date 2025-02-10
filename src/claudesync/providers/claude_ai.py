import urllib.request
import urllib.error
import urllib.parse
import json
import gzip
import time
import functools
from datetime import datetime, timezone

from .base_claude_ai import BaseClaudeAIProvider
from ..exceptions import ProviderError
from ..config_manager import ConfigManager

def retry_with_backoff(max_retries=3, delay=1):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except ProviderError as e:
                    if attempt < max_retries - 1:
                        print(f"Retry attempt {attempt + 1} failed. Retrying in {delay} seconds...")
                        time.sleep(delay)
                        delay *= 2
                    else:
                        raise e
        return wrapper
    return decorator

class ClaudeAIProvider(BaseClaudeAIProvider):
    def __init__(self, session_key=None, session_key_expiry=None):
        super().__init__(session_key, session_key_expiry)
        self.config = ConfigManager()

    @retry_with_backoff(max_retries=5, delay=2)
    def _make_request(self, method, endpoint, data=None):
        url = f"{self.BASE_URL}{endpoint}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:129.0) Gecko/20100101 Firefox/129.0",
            "Content-Type": "application/json",
            "Accept-Encoding": "gzip",
            "Cookie": f"sessionKey={self.session_key}",
        }

        req = urllib.request.Request(url, method=method, headers=headers)
        if data:
            req.data = json.dumps(data).encode("utf-8")

        try:
            self.logger.debug(f"Making {method} request to {url}")
            self.logger.debug(f"Headers: {headers}")
            if data:
                self.logger.debug(f"Request data: {data}")

            with urllib.request.urlopen(req) as response:
                self.logger.debug(f"Response status code: {response.status}")
                self.logger.debug(f"Response headers: {response.headers}")

                if response.headers.get("Content-Encoding") == "gzip":
                    content = gzip.decompress(response.read())
                else:
                    content = response.read()

                content_str = content.decode("utf-8")
                self.logger.debug(f"Response content: {content_str[:1000]}...")

                if not content:
                    return None

                return json.loads(content_str)

        except urllib.error.HTTPError as e:
            self.handle_http_error(e)
        except urllib.error.URLError as e:
            self.logger.error(f"URL Error: {str(e)}")
            raise ProviderError(f"API request failed: {str(e)}")
        except json.JSONDecodeError as json_err:
            self.logger.error(f"Failed to parse JSON response: {str(json_err)}")
            self.logger.error(f"Response content: {content_str}")
            raise ProviderError(f"Invalid JSON response from API: {str(json_err)}")

    def handle_http_error(self, e):
        self.logger.debug(f"Request failed: {str(e)}")
        self.logger.debug(f"Response status code: {e.code}")
        self.logger.debug(f"Response headers: {e.headers}")
        content = e.read().decode("utf-8")
        self.logger.debug(f"Response content: {content}")
        if e.code == 403:
            error_msg = "Received a 403 Forbidden error. Your session key might be invalid. Please try logging out and logging in again."
            self.logger.error(error_msg)
            raise ProviderError(error_msg)
        if e.code == 429:
            try:
                error_data = json.loads(content)
                resets_at_unix = json.loads(error_data["error"]["message"])["resetsAt"]
                resets_at_local = datetime.fromtimestamp(resets_at_unix, tz=timezone.utc).astimezone()
                formatted_time = resets_at_local.strftime("%a %b %d %Y %H:%M:%S %Z%z")
                print(f"Message limit exceeded. Try again after {formatted_time}")
            except (KeyError, json.JSONDecodeError) as parse_error:
                print(f"Failed to parse error response: {parse_error}")
            raise ProviderError("HTTP 429: Too Many Requests")
        raise ProviderError(f"API request failed: {str(e)}")

    def _make_request_stream(self, method, endpoint, data=None):
        url = f"{self.BASE_URL}{endpoint}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:129.0) Gecko/20100101 Firefox/129.0",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            "Cookie": f"sessionKey={self.session_key}",
        }

        req = urllib.request.Request(url, method=method, headers=headers)
        if data:
            req.data = json.dumps(data).encode("utf-8")

        try:
            return urllib.request.urlopen(req)
        except urllib.error.HTTPError as e:
            self.handle_http_error(e)
        except urllib.error.URLError as e:
            raise ProviderError(f"API request failed: {str(e)}")