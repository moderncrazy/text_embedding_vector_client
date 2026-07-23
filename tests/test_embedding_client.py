import importlib.util
import sys
import types
import unittest
from pathlib import Path
from types import SimpleNamespace


class StubTool:
    def create_json_message(self, value):
        return ("json", value)

    def create_text_message(self, value):
        return ("text", value)


class StubTextEmbeddingModelConfig:
    def __init__(self, **values):
        self.values = values


def load_embedding_client_module():
    dify_plugin = types.ModuleType("dify_plugin")
    dify_plugin.Tool = StubTool

    entities = types.ModuleType("dify_plugin.entities")
    model = types.ModuleType("dify_plugin.entities.model")
    text_embedding = types.ModuleType("dify_plugin.entities.model.text_embedding")
    text_embedding.TextEmbeddingModelConfig = StubTextEmbeddingModelConfig
    tool = types.ModuleType("dify_plugin.entities.tool")
    tool.ToolInvokeMessage = object

    replacements = {
        "dify_plugin": dify_plugin,
        "dify_plugin.entities": entities,
        "dify_plugin.entities.model": model,
        "dify_plugin.entities.model.text_embedding": text_embedding,
        "dify_plugin.entities.tool": tool,
    }
    previous = {name: sys.modules.get(name) for name in replacements}
    sys.modules.update(replacements)

    try:
        source = Path(__file__).parents[1] / "tools" / "embedding-client.py"
        spec = importlib.util.spec_from_file_location("embedding_client", source)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        for name, original in previous.items():
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original


embedding_client = load_embedding_client_module()


class EmbeddingClientTest(unittest.TestCase):
    def make_client(self, invoke):
        client = embedding_client.EmbeddingClient()
        client.session = SimpleNamespace(
            model=SimpleNamespace(
                text_embedding=SimpleNamespace(invoke=invoke),
            )
        )
        return client

    def invoke(self, client, input_text="hello"):
        return list(
            client._invoke(
                {
                    "embedding_model_config": {"model": "test"},
                    "input_text": input_text,
                    "batch_size": 10,
                }
            )
        )

    def test_preserves_model_invocation_exception(self):
        expected = TimeoutError("embedding request timed out")

        def raise_timeout(**_kwargs):
            raise expected

        client = self.make_client(raise_timeout)

        with self.assertRaises(TimeoutError) as caught:
            self.invoke(client)

        self.assertIs(caught.exception, expected)

    def test_missing_input_raises_value_error(self):
        client = self.make_client(lambda **_kwargs: None)

        with self.assertRaisesRegex(ValueError, "input_text"):
            self.invoke(client, input_text="")

    def test_response_without_embeddings_raises_runtime_error(self):
        client = self.make_client(lambda **_kwargs: SimpleNamespace())

        with self.assertRaisesRegex(RuntimeError, "embeddings"):
            self.invoke(client)

    def test_batch_embedding_count_mismatch_raises_runtime_error(self):
        response = SimpleNamespace(embeddings=[[0.1, 0.2]])
        client = self.make_client(lambda **_kwargs: response)

        with self.assertRaisesRegex(RuntimeError, "1 embeddings for 2 texts"):
            self.invoke(client, input_text='["first", "second"]')

    def test_empty_embedding_result_raises_runtime_error(self):
        client = self.make_client(lambda **_kwargs: None)

        with self.assertRaisesRegex(RuntimeError, "no embeddings"):
            self.invoke(client, input_text="[]")

    def test_success_emits_expected_json_message(self):
        response = SimpleNamespace(embeddings=[[0.1, 0.2], [0.3, 0.4]])
        client = self.make_client(lambda **_kwargs: response)

        messages = self.invoke(client, input_text='["first", "second"]')

        self.assertEqual(
            messages,
            [("json", {"vector": [[0.1, 0.2], [0.3, 0.4]]})],
        )


if __name__ == "__main__":
    unittest.main()
