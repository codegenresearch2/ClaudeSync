import unittest
from unittest.mock import patch, MagicMock
import urllib.request
import gzip
import io
from claudesync.providers.claude_ai import ClaudeAIProvider
from claudesync.exceptions import ProviderError

class TestClaudeAIProvider(unittest.TestCase):

    def setUp(self):
        self.provider = ClaudeAIProvider(
            "test_session_key", "Tue, 03 Sep 2099 06:51:21 UTC"
        )
        self.mock_config = MagicMock()

    @patch("claudesync.config_manager.ConfigManager.get_session_key")
    def test_make_request_success(self, mock_get_session_key):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b'{"key": "value"}'
        mock_response.getheader.side_effect = lambda header: {
            "Content-Type": "application/json"
        }.get(header)

        def urlopen_side_effect(*args, **kwargs):
            class FakeResponse:
                def __init__(self, response):
                    self.response = response

                def read(self):
                    return self.response

                def getheader(self, header):
                    return self.response.get(header)

                def __enter__(self):
                    return self

                def __exit__(self, exc_type, exc_val, exc_tb):
                    pass

            return FakeResponse(mock_response)

        with patch("urllib.request.urlopen", side_effect=urlopen_side_effect):
            mock_get_session_key.return_value = "sk-ant-1234"
            result = self.provider._make_request("GET", "/test")

            self.assertEqual(result, {"key": "value"})
            mock_get_session_key.assert_called_once()

    @patch("urllib.request.urlopen")
    def test_make_request_failure(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError("Test error")

        with self.assertRaises(ProviderError):
            self.provider._make_request("GET", "/test")

    @patch("claudesync.config_manager.ConfigManager.get_session_key")
    @patch("urllib.request.urlopen")
    def test_make_request_403_error(self, mock_urlopen, mock_get_session_key):
        mock_response = MagicMock()
        mock_response.status = 403
        mock_response.read.return_value = b'{"error": "Forbidden"}'
        mock_response.getheader.side_effect = lambda header: {
            "Content-Type": "application/json"
        }.get(header)

        def urlopen_side_effect(*args, **kwargs):
            class FakeResponse:
                def __init__(self, response):
                    self.response = response

                def read(self):
                    return self.response

                def getheader(self, header):
                    return self.response.get(header)

                def __enter__(self):
                    return self

                def __exit__(self, exc_type, exc_val, exc_tb):
                    pass

            return FakeResponse(mock_response)

        with patch("urllib.request.urlopen", side_effect=urlopen_side_effect):
            mock_get_session_key.return_value = "sk-ant-1234"

            with self.assertRaises(ProviderError) as context:
                self.provider._make_request("GET", "/test")

            self.assertIn("403 Forbidden error", str(context.exception))

    @patch("urllib.request.urlopen")
    def test_make_request_gzip_response(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = gzip.compress(b'{"key": "value"}')
        mock_response.getheader.side_effect = lambda header: {
            "Content-Type": "application/json",
            "Content-Encoding": "gzip"
        }.get(header)

        def urlopen_side_effect(*args, **kwargs):
            class FakeResponse:
                def __init__(self, response):
                    self.response = response

                def read(self):
                    return self.response

                def getheader(self, header):
                    return self.response.get(header)

                def __enter__(self):
                    return self

                def __exit__(self, exc_type, exc_val, exc_tb):
                    pass

            return FakeResponse(mock_response)

        with patch("urllib.request.urlopen", side_effect=urlopen_side_effect):
            result = self.provider._make_request("GET", "/test")

            self.assertEqual(result, {"key": "value"})

if __name__ == "__main__":
    unittest.main()