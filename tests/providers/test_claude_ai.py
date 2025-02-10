import unittest
from unittest.mock import patch, MagicMock
import urllib.request
import urllib.error
import gzip
import io
import json
from claudesync.providers.claude_ai import ClaudeAIProvider
from claudesync.exceptions import ProviderError

class TestClaudeAIProvider(unittest.TestCase):

    def setUp(self):
        self.provider = ClaudeAIProvider(
            "test_session_key", "Tue, 03 Sep 2099 06:51:21 UTC"
        )
        self.mock_config = MagicMock()

    @patch("urllib.request.urlopen")
    @patch("claudesync.config_manager.ConfigManager.get_session_key")
    def test_make_request_success(self, mock_get_session_key, mock_urlopen):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = {'Content-Type': 'application/json'}
        mock_response.__enter__.return_value.read.return_value = json.dumps({"key": "value"}).encode('utf-8')
        mock_urlopen.return_value = mock_response

        mock_get_session_key.return_value = "sk-ant-1234"

        result = self.provider._make_request("GET", "/test")

        self.assertEqual(result, {"key": "value"})
        mock_urlopen.assert_called_once()

    @patch("urllib.request.urlopen")
    @patch("claudesync.config_manager.ConfigManager.get_session_key")
    def test_make_request_403_error(self, mock_get_session_key, mock_urlopen):
        mock_response = MagicMock()
        mock_response.status = 403
        mock_response.headers = {'Content-Type': 'application/json'}
        mock_response.__enter__.return_value.read.return_value = json.dumps({"error": "Forbidden"}).encode('utf-8')
        mock_urlopen.return_value = mock_response

        mock_get_session_key.return_value = "sk-ant-1234"

        with self.assertRaises(ProviderError):
            self.provider._make_request("GET", "/test")

    @patch("urllib.request.urlopen")
    @patch("claudesync.config_manager.ConfigManager.get_session_key")
    def test_make_request_gzip_response(self, mock_get_session_key, mock_urlopen):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = {'Content-Encoding': 'gzip'}
        gzip_content = io.BytesIO()
        with gzip.GzipFile(fileobj=gzip_content, mode='w') as gzip_file:
            gzip_file.write(json.dumps({"key": "value"}).encode('utf-8'))
        gzip_content.seek(0)
        mock_response.__enter__.return_value.read.return_value = gzip_content.read()
        mock_urlopen.return_value = mock_response

        mock_get_session_key.return_value = "sk-ant-1234"

        result = self.provider._make_request("GET", "/test")

        self.assertEqual(result, {"key": "value"})
        mock_urlopen.assert_called_once()

if __name__ == "__main__":
    unittest.main()