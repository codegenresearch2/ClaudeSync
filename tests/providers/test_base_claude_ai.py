import datetime
import unittest
from unittest.mock import patch, MagicMock
from claudesync.providers.base_claude_ai import BaseClaudeAIProvider
import click


class TestBaseClaudeAIProvider(unittest.TestCase):

    def setUp(self):
        self.provider = BaseClaudeAIProvider("test_session_key")

    @patch("claudesync.cli.main.ConfigManager")
    @patch("claudesync.providers.base_claude_ai.click.echo")
    @patch("urllib.request.urlopen")
    def test_login(self, mock_urlopen, mock_echo, mock_config_manager):
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"organizations": [{"id": "org1", "name": "Test Org"}]}'
        mock_urlopen.return_value = mock_response

        session_key = "sk-ant-test123"
        expires = "Tue, 03 Sep 2099 05:49:08 GMT"
        mock_echo.side_effect = [session_key, expires]

        result = self.provider.login()

        self.assertEqual(
            result, (session_key, datetime.datetime(2099, 9, 3, 5, 49, 8))
        )
        self.assertEqual(self.provider.session_key, session_key)
        mock_echo.assert_called()

    @patch("claudesync.cli.main.ConfigManager")
    @patch("claudesync.providers.base_claude_ai.click.echo")
    @patch("urllib.request.urlopen")
    def test_login_invalid_key(self, mock_urlopen, mock_echo, mock_config_manager):
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"organizations": [{"id": "org1", "name": "Test Org"}]}'
        mock_urlopen.return_value = mock_response

        session_key = "sk-ant-test123"
        expires = "Tue, 03 Sep 2099 05:49:08 GMT"
        mock_echo.side_effect = ["invalid_key", session_key, expires]

        result = self.provider.login()

        self.assertEqual(
            result, (session_key, datetime.datetime(2099, 9, 3, 5, 49, 8))
        )
        self.assertEqual(mock_echo.call_count, 3)

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

    def test_make_request_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            self.provider._make_request("GET", "/test")


if __name__ == "__main__":
    unittest.main()