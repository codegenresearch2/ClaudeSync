import json\\\nimport requests\\\nfrom .base_claude_ai import BaseClaudeAIProvider\\\nfrom ..exceptions import ProviderError\\\\\n\\nclass ClaudeAIProvider(BaseClaudeAIProvider):\\\\\\n    def _make_request(self, method, endpoint, data=None):\\\\\\\n        url = f"{{self.BASE_URL}}{{endpoint}}\