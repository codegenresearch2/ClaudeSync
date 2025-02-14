import unittest
from unittest.mock import patch, MagicMock
import urllib.request
import json
from claudesync.providers.claude_ai import ClaudeAIProvider
from claudesync.exceptions import ProviderError
import getpass

class TestClaudeAIProvider(unittest.TestCase):

    def setUp(self):
        self.provider = ClaudeAIProvider("test_session_key")
        self.mock_config = MagicMock()

    @patch("claudesync.config_manager.ConfigManager.get_session_key")
    @patch("claudesync.providers.claude_ai.urllib.request.urlopen")
    def test_make_request_success(self, mock_urlopen, mock_get_session_key):
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = json.dumps({"key": "value"}).encode('utf-8')
        mock_urlopen.return_value = mock_response

        mock_get_session_key.return_value = "sk-ant-1234"

        result = self.provider._make_request("GET", "/test")

        self.assertEqual(result, {"key": "value"})
        mock_urlopen.assert_called_once()

    @patch("claudesync.providers.claude_ai.urllib.request.urlopen")
    def test_make_request_failure(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError("Test error")

        with self.assertRaises(ProviderError):
            self.provider._make_request("GET", "/test")

    @patch("claudesync.config_manager.ConfigManager.get_session_key")
    @patch("claudesync.providers.claude_ai.urllib.request.urlopen")
    def test_make_request_403_error(self, mock_urlopen, mock_get_session_key):
        mock_response = MagicMock()
        mock_response.getcode.return_value = 403
        mock_urlopen.return_value = mock_response

        mock_get_session_key.return_value = "sk-ant-1234"

        with self.assertRaises(ProviderError) as context:
            self.provider._make_request("GET", "/test")

        self.assertIn("403 Forbidden error", str(context.exception))

    @patch("claudesync.providers.base_claude_ai.click.prompt")
    @patch("claudesync.providers.base_claude_ai.getpass.getpass")
    def test_login(self, mock_getpass, mock_prompt):
        mock_getpass.return_value = "sk-ant-test123"
        mock_prompt.return_value = "Tue, 03 Sep 2099 05:49:08 GMT"
        self.provider.get_organizations = MagicMock(return_value=[{"id": "org1", "name": "Test Org"}])

        result = self.provider.login()

        self.assertEqual(result, ("sk-ant-test123", "Tue, 03 Sep 2099 05:49:08 GMT"))
        self.assertEqual(self.provider.session_key, "sk-ant-test123")


This code tests the `ClaudeAIProvider` class using `unittest`. The tests cover various scenarios, including successful requests, requests that fail, and requests that return a 403 Forbidden error. The tests use `urllib` instead of `requests` for HTTP requests, and they hide sensitive input during login prompts using `getpass`. The tests also handle session key expiry more flexibly by allowing for manual input of the expiry time.