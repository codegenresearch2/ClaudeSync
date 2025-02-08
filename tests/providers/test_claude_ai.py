import unittest\\\\nfrom unittest.mock import patch, MagicMock, call, ANY\\\\nimport requests\\\\\nfrom claudesync.providers.claude_ai import ClaudeAIProvider\\\\\nfrom claudesync.exceptions import ProviderError\\\\\nimport json\\\\n\\\\n\\\\nclass TestClaudeAIProvider(unittest.TestCase):\\\\n\\\\n    def setUp(self):\\\\n        self.provider = ClaudeAIProvider(\"test_session_key\", \"Tue, 03 Sep 2099 06:51:21 UTC\") \\\\n        self.mock_config = MagicMock()\\\\n\\\\n    @patch(\"claudesync.config_manager.ConfigManager.get_session_key\") \\\\n    @patch(\"claudesync.providers.claude_ai.requests.request\") \\\\n    def test_make_request_success(self, mock_request, mock_get_session_key): \\\\n        mock_response = MagicMock() \\\\n        mock_response.status_code = 200 \\\\n        mock_response.json.return_value = {\"key\": \"value\"} \\\\n        mock_request.return_value = mock_response \\\\n\\\\n        mock_get_session_key.return_value = \"sk-ant-1234\" \\\\n\\\\n        result = self.provider._make_request(\"GET\", \"/test\") \\\\n\\\\n        self.assertEqual(result, {\"key\": \"value\"}) \\\\n        mock_request.assert_called_once() \\\\n\\\\n    @patch(\"claudesync.providers.claude_ai.requests.request\") \\\\n    def test_make_request_failure(self, mock_request): \\\\n        mock_request.side_effect = requests.RequestException(\"Test error\") \\\\n\\\\n        with self.assertRaises(ProviderError): \\\\n            self.provider._make_request(\"GET\", \"/test\") \\\\n\\\\n    @patch(\"claudesync.config_manager.ConfigManager.get_session_key\") \\\\n    @patch(\"claudesync.providers.claude_ai.requests.request\") \\\\n    def test_make_request_403_error(self, mock_request, mock_get_session_key): \\\\n        mock_response = MagicMock() \\\\n        mock_response.status_code = 403 \\\\n        mock_request.return_value = mock_response \\\\n\\\\n        mock_get_session_key.return_value = \"sk-ant-1234\" \\\\n\\\\n        with self.assertRaises(ProviderError) as context: \\\\n            self.provider._make_request(\"GET\", \"/test\") \\\\n\\\\n        self.assertIn(\"403 Forbidden error\", str(context.exception)) \\\\n