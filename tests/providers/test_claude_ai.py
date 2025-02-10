import unittest
from unittest.mock import patch, MagicMock
import urllib.request
import json
from claudesync.providers.claude_ai import ClaudeAIProvider
from claudesync.exceptions import ProviderError
from getpass import getpass

class TestClaudeAIProvider(unittest.TestCase):

    def setUp(self):
        self.provider = ClaudeAIProvider("test_session_key", "Tue, 03 Sep 2099 06:51:21 UTC")
        self.mock_config = MagicMock()

    @patch("claudesync.config_manager.ConfigManager.get_session_key")
    @patch("urllib.request.urlopen")
    def test_make_request_success(self, mock_urlopen, mock_get_session_key):
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = json.dumps({"key": "value"}).encode('utf-8')
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
        mock_response.getcode.return_value = 403
        mock_urlopen.return_value = mock_response

        mock_get_session_key.return_value = "sk-ant-1234"

        with self.assertRaises(ProviderError) as context:
            self.provider._make_request("GET", "/test")

        self.assertIn("403 Forbidden error", str(context.exception))

    @patch("claudesync.providers.base_claude_ai.click.echo")
    @patch("getpass.getpass")
    def test_login(self, mock_getpass, mock_echo):
        mock_getpass.side_effect = ["sk-ant-test123"]
        self.provider.get_organizations = MagicMock(
            return_value=[{"id": "org1", "name": "Test Org"}]
        )

        result = self.provider.login()

        self.assertEqual(result, "sk-ant-test123")
        self.assertEqual(self.provider.session_key, "sk-ant-test123")
        mock_echo.assert_called()
        mock_getpass.assert_called_once_with("Please enter your sessionKey: ")


In the rewritten code, I have replaced `requests` with `urllib` for making HTTP requests. I have also replaced `click.prompt` with `getpass.getpass` to hide sensitive input during login prompts. The session key expiry is handled more flexibly by not requiring an expiry time during login and allowing the user to re-login when the session key expires.