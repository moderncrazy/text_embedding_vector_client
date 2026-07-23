import json
from collections.abc import Generator
from typing import List, Union, Sequence, Any

from dify_plugin import Tool
from dify_plugin.entities.model.text_embedding import TextEmbeddingModelConfig
from dify_plugin.entities.tool import ToolInvokeMessage


def chunked(seq: Sequence, size: int):
    for i in range(0, len(seq), size):
        yield seq[i:i + size]


def _parse_input_text(input_text: str) -> List[str]:
    """
    支持两种输入格式：
    1. 普通字符串，例如: "大家好我是小小"
    2. JSON 字符串数组，例如: ["大家好我是小小","今天很开心"]

    Supported input formats:
    1. Plain string, e.g., "大家好我是小小"
    2. JSON string array, e.g., ["大家好我是小小","今天很开心"]
    """

    try:
        parsed = json.loads(input_text)
        if isinstance(parsed, list) and all(isinstance(i, str) for i in parsed):
            return parsed
        else:
            # 如果解析出来不是字符串列表，则退回单字符串模式
            return [input_text]
    except json.JSONDecodeError:
        # 如果不是合法的 JSON，就当作普通字符串处理
        return [input_text]


class EmbeddingClient(Tool):
    """
    Dify 工具: 文本向量化
    在同一次工作流执行中复用 client，不同工作流之间会自动重建。

    Dify Tool: Text Embedding
    Reuses the same client within a single workflow execution, and automatically recreates between different workflow executions.
    """

    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        embedding_model_config = tool_parameters.get("embedding_model_config")
        input_text: Union[str, List[str]] = tool_parameters.get("input_text")
        batch_size: int = tool_parameters.get("batch_size") or 10

        if not input_text:
            raise ValueError("Missing 'input_text' parameter")

        input_text = _parse_input_text(input_text)
        results: List[List[float]] = []

        for batch in chunked(input_text, batch_size):
            model_config = TextEmbeddingModelConfig(**embedding_model_config)
            response = self.session.model.text_embedding.invoke(model_config=model_config, texts=batch)

            if not hasattr(response, "embeddings"):
                raise RuntimeError("Embedding service response is missing the 'embeddings' field")
            if len(response.embeddings) != len(batch):
                raise RuntimeError(
                    f"Embedding service returned {len(response.embeddings)} embeddings "
                    f"for {len(batch)} texts"
                )

            results.extend(response.embeddings)

        if not results:
            raise RuntimeError("Embedding service returned no embeddings")

        yield self.create_json_message({
            "vector": results
        })
