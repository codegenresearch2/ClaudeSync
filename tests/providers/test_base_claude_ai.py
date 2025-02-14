import datetime
import unittest
from unittest.mock import patch, MagicMock
from urllib.request import Request, urlopen
import gzip
import io

class BaseClaudeAIProvider:
    def __init__(self, session_key):
        self.session_key = session_key

    def _make_request(self, method, url, data=None):
        headers = {'Authorization': f'Bearer {self.session_key}'}
        req = Request(url, method=method, headers=headers)
        if data:
            req.data = data.encode('utf-8')
        with urlopen(req) as response:
            if response.info().get('Content-Encoding') == 'gzip':
                buf = io.BytesIO(response.read())
                with gzip.GzipFile(fileobj=buf) as f:
                    return f.read().decode('utf-8')
            else:
                return response.read().decode('utf-8')

    def get_organizations(self):
        url = "https://api.claude.ai/organizations"
        response = self._make_request("GET", url)
        organizations = [org for org in response if 'chat' in org['capabilities'] and 'claude_pro' in org['capabilities']]
        return organizations

    def get_projects(self, org_id):
        url = f"https://api.claude.ai/organizations/{org_id}/projects"
        response = self._make_request("GET", url)
        projects = [proj for proj in response if proj['archived_at'] is None]
        return projects

    def login(self):
        session_key = input("Please enter your sessionKey: ")
        expires = input("Please enter the expires time for the sessionKey: ")
        self.session_key = session_key
        return session_key, datetime.datetime.strptime(expires, "%a, %d %b %Y %H:%M:%S %Z")

class TestBaseClaudeAIProvider(unittest.TestCase):
    def setUp(self):
        self.provider = BaseClaudeAIProvider("test_session_key")

    @patch("urllib.request.urlopen")
    def test_make_request(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.info.return_value = {'Content-Encoding': 'gzip'}
        mock_response.read.return_value = b'{"key": "value"}'
        mock_buffer = io.BytesIO(b'\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\xff\x06\x00\x42\x5a\x68\x34\x2e\x34\x2e\x33\x20\x28\x53\x61\x6d\x73\x75\x6e\x67\x20\x31\x34\x2e\x30\x2e\x32\x29\x20\x4f\x70\x65\x6e\x53\x53\x4c\x20\x33\x2e\x30\x2e\x32\x31\x00\x03\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
        mock_urlopen.return_value = mock_response
        mock_response.read.return_value = mock_buffer.read()

        result = self.provider._make_request("GET", "https://api.claude.ai/test")
        self.assertEqual(result, '{"key": "value"}')

    @patch("builtins.input")
    def test_login(self, mock_input):
        mock_input.side_effect = ["sk-ant-test123", "Tue, 03 Sep 2099 05:49:08 GMT"]
        self.provider.get_organizations = MagicMock(return_value=[{"id": "org1", "name": "Test Org"}])

        result = self.provider.login()
        self.assertEqual(result, ("sk-ant-test123", datetime.datetime(2099, 9, 3, 5, 49, 8)))
        self.assertEqual(self.provider.session_key, "sk-ant-test123")

    @patch("builtins.input")
    def test_login_invalid_key(self, mock_input):
        mock_input.side_effect = ["invalid_key", "sk-ant-test123", "Tue, 03 Sep 2099 05:49:08 GMT"]
        self.provider.get_organizations = MagicMock(return_value=[{"id": "org1", "name": "Test Org"}])

        result = self.provider.login()
        self.assertEqual(result, ("sk-ant-test123", datetime.datetime(2099, 9, 3, 5, 49, 8)))

    @patch("urllib.request.urlopen")
    def test_get_organizations(self, mock_urlopen):
        mock_response = [
            {"uuid": "org1", "name": "Org 1", "capabilities": ["chat", "claude_pro"]},
            {"uuid": "org2", "name": "Org 2", "capabilities": ["chat"]},
            {"uuid": "org3", "name": "Org 3", "capabilities": ["chat", "claude_pro"]},
        ]
        mock_urlopen.return_value.read.return_value = json.dumps(mock_response).encode('utf-8')

        result = self.provider.get_organizations()
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["id"], "org1")
        self.assertEqual(result[1]["id"], "org3")

    @patch("urllib.request.urlopen")
    def test_get_projects(self, mock_urlopen):
        mock_response = [
            {"uuid": "proj1", "name": "Project 1", "archived_at": None},
            {"uuid": "proj2", "name": "Project 2", "archived_at": "2023-01-01"},
            {"uuid": "proj3", "name": "Project 3", "archived_at": None},
        ]
        mock_urlopen.return_value.read.return_value = json.dumps(mock_response).encode('utf-8')

        result = self.provider.get_projects("org1")
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["id"], "proj1")
        self.assertEqual(result[1]["id"], "proj3")

    def test_make_request_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            self.provider._make_request("GET", "/test")

if __name__ == "__main__":
    unittest.main()