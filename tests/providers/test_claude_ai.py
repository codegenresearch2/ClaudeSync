import unittest\nfrom unittest.mock import patch, MagicMock\nimport urllib.request\nimport urllib.error\nfrom claudesync.providers.claude_ai import ClaudeAIProvider\nfrom claudesync.exceptions import ProviderError\nimport json\n\n\nclass TestClaudeAIProvider(unittest.TestCase):\n\n    def setUp(self):\n        self.provider = ClaudeAIProvider(\