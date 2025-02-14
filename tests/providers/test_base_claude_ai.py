import datetime
import unittest
from unittest.mock import patch, MagicMock, call, ANY
from urllib.request import Request, urlopen
from urllib.parse import urlencode
import gzip
import json
from claudesync.providers.base_claude_ai import BaseClaudeAIProvider
import click

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
            call("Please provide your session key", type=str),
            call(
                "Please provide the expiration time for the session key",
                default=ANY,
                type=str,
            ),
        ]

        mock_prompt.assert_has_calls(expected_calls, any_order=True)

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

class BaseClaudeAIProvider:
    def __init__(self, session_key, expires=None):
        self.session_key = session_key
        self.expires = expires

    def login(self):
        session_key = click.prompt("Please provide your session key", type=str)
        expires = click.prompt("Please provide the expiration time for the session key", default=ANY, type=str)
        self.session_key = session_key
        return session_key, datetime.datetime.strptime(expires, "%a, %d %b %Y %H:%M:%S %Z")

    def get_organizations(self):
        orgs = self._make_request("GET", "/organizations")
        return [org for org in orgs if "chat" in org["capabilities"] and "claude_pro" in org["capabilities"]]

    def get_projects(self, org_id):
        projects = self._make_request("GET", f"/organizations/{org_id}/projects")
        return [project for project in projects if project["archived_at"] is None]

    def _make_request(self, method, path, data=None):
        url = "https://api.claude.ai" + path
        headers = {
            "Authorization": f"Bearer {self.session_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Accept-Encoding": "gzip"
        }

        if data:
            data = json.dumps(data).encode("utf-8")

        req = Request(url, data=data, headers=headers, method=method)
        response = urlopen(req)

        if response.info().get("Content-Encoding") == "gzip":
            response_data = gzip.decompress(response.read())
        else:
            response_data = response.read()

        return json.loads(response_data)