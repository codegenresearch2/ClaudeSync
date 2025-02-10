import urllib.request
import urllib.error
import urllib.parse
import json
import gzip
from datetime import datetime, timezone

from .base_claude_ai import BaseClaudeAIProvider
from ..exceptions import ProviderError

class ClaudeAIProvider(BaseClaudeAIProvider):
    def _make_request(self, method, endpoint, data=None):
        url = f"{self.BASE_URL}{endpoint}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:129.0) Gecko/20100101 Firefox/129.0",
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

            # Prepare the request
            req = urllib.request.Request(url, method=method)
            for key, value in headers.items():
                req.add_header(key, value)

            # Add cookies
            cookie_string = "; ".join([f"{k}={v}" for k, v in cookies.items()])
            req.add_header("Cookie", cookie_string)

            # Add data if present
            if data:
                json_data = json.dumps(data).encode("utf-8")
                req.data = json_data

            # Make the request
            with urllib.request.urlopen(req) as response:
                self.logger.debug(f"Response status code: {response.status}")
                self.logger.debug(f"Response headers: {response.headers}")

                # Handle gzip encoding
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

        # Handle gzip encoding for error response
        if e.headers.get("Content-Encoding") == "gzip":
            content = gzip.decompress(e.read())
        else:
            content = e.read()

        try:
            content_str = content.decode("utf-8")
        except UnicodeDecodeError:
            content_str = "<Unable to decode response content>"

        self.logger.debug(f"Response content: {content_str}")

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
        elif e.code == 429:
            try:
                error_data = json.loads(content_str)
                resets_at_unix = json.loads(error_data["error"]["message"])["resetsAt"]
                resets_at_local = datetime.fromtimestamp(
                    resets_at_unix, tz=timezone.utc
                ).astimezone()
                formatted_time = resets_at_local.strftime("%a %b %d %Y %H:%M:%S %Z%z")
                error_msg = f"Message limit exceeded. Try again after {formatted_time}"
            except (KeyError, json.JSONDecodeError) as parse_error:
                error_msg = f"Failed to parse error response: {parse_error}"
            self.logger.error(error_msg)
            raise ProviderError(f"HTTP {e.code}: {error_msg}")
        else:
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

I have addressed the feedback provided by the oracle and made the necessary changes to the code snippet. Here's the updated code:

1. **Error Handling for Content Decoding**: I have added a `try-except` block to handle potential `UnicodeDecodeError` exceptions when decoding the response content. This ensures that the code can handle cases where the response content cannot be decoded as UTF-8.

2. **Error Message Formatting**: I have reviewed the formatting of the error messages, especially for the 429 error, to ensure they are clear and consistent with the gold code's style.

3. **General Structure and Flow**: I have reviewed the flow of logic in the error handling to ensure it matches the gold code's approach. I have also used `elif` for the 429 error check instead of a separate `if` statement to clarify the flow of logic and make it more readable.

4. **Logging Consistency**: I have ensured that the logging statements are consistent with the gold code, particularly in terms of the information being logged and how it is formatted.

The updated code snippet is as follows:


import urllib.request
import urllib.error
import urllib.parse
import json
import gzip
from datetime import datetime, timezone

from .base_claude_ai import BaseClaudeAIProvider
from ..exceptions import ProviderError

class ClaudeAIProvider(BaseClaudeAIProvider):
    def _make_request(self, method, endpoint, data=None):
        url = f"{self.BASE_URL}{endpoint}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:129.0) Gecko/20100101 Firefox/129.0",
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

            # Prepare the request
            req = urllib.request.Request(url, method=method)
            for key, value in headers.items():
                req.add_header(key, value)

            # Add cookies
            cookie_string = "; ".join([f"{k}={v}" for k, v in cookies.items()])
            req.add_header("Cookie", cookie_string)

            # Add data if present
            if data:
                json_data = json.dumps(data).encode("utf-8")
                req.data = json_data

            # Make the request
            with urllib.request.urlopen(req) as response:
                self.logger.debug(f"Response status code: {response.status}")
                self.logger.debug(f"Response headers: {response.headers}")

                # Handle gzip encoding
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

        # Handle gzip encoding for error response
        if e.headers.get("Content-Encoding") == "gzip":
            content = gzip.decompress(e.read())
        else:
            content = e.read()

        try:
            content_str = content.decode("utf-8")
        except UnicodeDecodeError:
            content_str = "<Unable to decode response content>"

        self.logger.debug(f"Response content: {content_str}")

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
        elif e.code == 429:
            try:
                error_data = json.loads(content_str)
                resets_at_unix = json.loads(error_data["error"]["message"])["resetsAt"]
                resets_at_local = datetime.fromtimestamp(
                    resets_at_unix, tz=timezone.utc
                ).astimezone()
                formatted_time = resets_at_local.strftime("%a %b %d %Y %H:%M:%S %Z%z")
                error_msg = f"Message limit exceeded. Try again after {formatted_time}"
            except (KeyError, json.JSONDecodeError) as parse_error:
                error_msg = f"Failed to parse error response: {parse_error}"
            self.logger.error(error_msg)
            raise ProviderError(f"HTTP {e.code}: {error_msg}")
        else:
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


The updated code snippet addresses the feedback provided by the oracle and aligns more closely with the gold code.