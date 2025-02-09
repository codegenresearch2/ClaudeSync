import datetime
import unittest
from unittest.mock import patch, MagicMock
from claudesync.providers.base_claude_ai import BaseClaudeAIProvider
import click


class TestBaseClaudeAIProvider(unittest.TestCase):

    def setUp(self):
        self.provider = BaseClaudeAIProvider("test_session_key")

    @patch("claudesync.cli.main.ConfigManager")
    @patch("claudesync.providers.base_claude_ai.click.prompt")
    def test_login(self, mock_prompt, mock_config_manager):
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
        expected_calls = [
            click.prompt("Please enter your sessionKey", type=str),
            click.prompt(
                "Please enter the expires time for the sessionKey",
                default="Tue, 03 Sep 2099 05:49:08 GMT",
                type=str,
            ),
        ]
        mock_prompt.assert_has_calls(expected_calls, any_order=True)

    @patch("claudesync.cli.main.ConfigManager")
    @patch("claudesync.providers.base_claude_ai.click.prompt")
    def test_login_invalid_key(self, mock_prompt, mock_config_manager):
        mock_prompt.side_effect = ["invalid_key", "sk-ant-test123", "Tue, 03 Sep 2099 05:49:08 GMT"]
        self.provider.get_organizations = MagicMock(
            return_value=[{"id": "org1", "name": "Test Org"}]
        )
        mock_config_manager.return_value = MagicMock()

        result = self.provider.login()

        self.assertEqual(
            result, ("sk-ant-test123", datetime.datetime(2099, 9, 3, 5, 49, 8))
        )
        self.assertEqual(mock_prompt.call_count, 3)
        expected_calls = [
            click.prompt("Please enter your sessionKey", type=str),
            click.prompt("Please enter your sessionKey", type=str),
            click.prompt(
                "Please enter the expires time for the sessionKey",
                default="Tue, 03 Sep 2099 05:49:08 GMT",
                type=str,
            ),
        ]
        mock_prompt.assert_has_calls(expected_calls, any_order=True)


if __name__ == "__main__":
    unittest.main()