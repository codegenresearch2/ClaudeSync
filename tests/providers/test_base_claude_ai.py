import datetime
import unittest
from unittest.mock import patch, MagicMock, call, ANY
from claudesync.providers.base_claude_ai import BaseClaudeAIProvider
import urllib.request
import json
import gzip
import io

class TestBaseClaudeAIProvider(unittest.TestCase):

    def setUp(self):
        self.provider = BaseClaudeAIProvider("test_session_key")

    @patch("claudesync.cli.main.ConfigManager")
    @patch("claudesync.providers.base_claude_ai.click.echo")
    @patch("claudesync.providers.base_claude_ai.click.prompt")
    def test_login(self, mock_prompt, mock_echo, mock_config_manager):
        mock_prompt.side_effect = ["sk-ant-test123", "Tue, 03 Sep 2099 05:49:08 GMT"]
        self.provider.get_organizations = MagicMock(
            return_value=[{"id": "org1", "name": "Test Org"}]
        )
        mock_config_manager.return_value = MagicMock()

        result = self.provider.login()

        self.assertEqual(
            result, ("sk-ant-test123", datetime.datetime(2099, 9, 3, 5, 49, 8))
        )
        self.assertEqual(self.provider.session_key, "sk-ant-test123")
        mock_echo.assert_called()

        expected_calls = [
            call("Please enter your sessionKey", type=str, hide_input=True),
            call(
                "Please enter the expires time for the sessionKey (optional)",
                default=ANY,
                type=str,
            ),
        ]

        mock_prompt.assert_has_calls(expected_calls, any_order=True)

    @patch("claudesync.cli.main.ConfigManager")
    @patch("claudesync.providers.base_claude_ai.click.echo")
    @patch("claudesync.providers.base_claude_ai.click.prompt")
    def test_login_invalid_key(self, mock_prompt, mock_echo, mock_config_manager):
        mock_prompt.side_effect = ["invalid_key", "sk-ant-test123", "Tue, 03 Sep 2099 05:49:08 GMT"]
        self.provider.get_organizations = MagicMock(
            return_value=[{"id": "org1", "name": "Test Org"}]
        )
        mock_config_manager.return_value = MagicMock()

        with self.assertRaises(Exception) as context:
            self.provider.login()

        self.assertTrue("Invalid session key" in str(context.exception))
        self.assertEqual(mock_prompt.call_count, 3)
        self.assertNotEqual(self.provider.session_key, "sk-ant-test123")

    @patch("claudesync.providers.base_claude_ai.BaseClaudeAIProvider._make_request")
    def test_get_organizations(self, mock_make_request):
        mock_make_request.return_value = [
            {"uuid": "org1", "name": "Org 1", "capabilities": ["chat", "claude_pro"]},
            {"uuid": "org2", "name": "Org 2", "capabilities": ["chat"]},
            {"uuid": "org3", "name": "Org 3", "capabilities": ["chat", "claude_pro"]},
        ]

        result = self.provider.get_organizations()

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["id"], "org1")
        self.assertEqual(result[1]["id"], "org3")

    @patch("claudesync.providers.base_claude_ai.BaseClaudeAIProvider._make_request")
    def test_get_projects(self, mock_make_request):
        mock_make_request.return_value = [
            {"uuid": "proj1", "name": "Project 1", "archived_at": None},
            {"uuid": "proj2", "name": "Project 2", "archived_at": "2023-01-01"},
            {"uuid": "proj3", "name": "Project 3", "archived_at": None},
        ]

        result = self.provider.get_projects("org1")

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["id"], "proj1")
        self.assertEqual(result[1]["id"], "proj3")

    def test_make_request(self):
        url = "https://example.com/api/endpoint"
        method = "GET"
        headers = {"Authorization": "Bearer test_session_key"}

        # Mock the response
        response_data = {"key": "value"}
        response = MagicMock()
        response.read.return_value = gzip.compress(json.dumps(response_data).encode())
        response.getheader.return_value = "application/json"

        # Mock the urllib.request.urlopen function
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value = response

            result = self.provider._make_request(method, url)

            # Assert that urlopen was called with the correct arguments
            mock_urlopen.assert_called_once_with(url, headers=headers)

            # Assert that the response was handled correctly
            self.assertEqual(result, response_data)

        # Test error handling
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = urllib.error.URLError("Test error")

            with self.assertRaises(Exception) as context:
                self.provider._make_request(method, url)

            # Assert that the error was logged
            self.assertTrue("Error making request" in str(context.exception))

if __name__ == "__main__":
    unittest.main()