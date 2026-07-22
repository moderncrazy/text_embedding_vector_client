from typing import Any

from dify_plugin import ToolProvider


class EmbeddingProvider(ToolProvider):
    def _validate_credentials(self, credentials: dict[str, Any]) -> dict:
        pass
