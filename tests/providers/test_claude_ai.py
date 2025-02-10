import unittest
from unittest.mock import patch, MagicMock
import urllib.request
import urllib.error
import json
from claudesync.providers.claude_ai import ClaudeAIProvider
from claudesync.exceptions import ProviderError

class TestClaudeAIProvider(unittest.TestCase):

    def setUp(self):
        self.provider = ClaudeAIProvider(
            "test_session_key", "Tue, 03 Sep 2099 06:51:21 UTC"
        )
        self.mock_config = MagicMock()

    @patch("claudesync.config_manager.ConfigManager.get_session_key")
    @patch("urllib.request.urlopen")
    def test_make_request_success(self, mock_urlopen, mock_get_session_key):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = json.dumps({"key": "value"}).encode('utf-8')
        mock_response.getheader.return_value = 'application/json'
        mock_urlopen.return_value = mock_response

        mock_get_session_key.return_value = "sk-ant-1234"

        result = self.provider._make_request("GET", "/test")

        self.assertEqual(result, {"key": "value"})
        mock_urlopen.assert_called_once()

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
        mock_response.read.return_value = json.dumps({"error": "Forbidden"}).encode('utf-8')
        mock_response.getheader.return_value = 'application/json'
        mock_urlopen.return_value = mock_response

        mock_get_session_key.return_value = "sk-ant-1234"

        with self.assertRaises(ProviderError) as context:
            self.provider._make_request("GET", "/test")

        self.assertIn("403 Forbidden error", str(context.exception))

    @patch("urllib.request.urlopen")
    def test_make_request_gzip_response(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b'{"key": "value"}'
        mock_response.getheader.return_value = 'application/json'
        mock_response.getheader.side_effect = lambda header: {'content-encoding': 'gzip'}.get(header)
        mock_urlopen.return_value = mock_response

        result = self.provider._make_request("GET", "/test")

        self.assertEqual(result, {"key": "value"})
        mock_urlopen.assert_called_once()

if __name__ == "__main__":
    unittest.main()