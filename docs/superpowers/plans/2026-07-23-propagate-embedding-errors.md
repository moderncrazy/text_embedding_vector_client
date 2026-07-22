# Propagate Embedding Errors Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ensure the plugin emits embedding vectors only on complete success and raises every condition that prevents a valid embedding result.

**Architecture:** Preserve the current generator interface, parsing, batching, and JSON success output. Remove the catch-all conversion to text messages, validate each model response before accumulating it, and let original model-provider exceptions cross the plugin boundary unchanged.

**Tech Stack:** Python 3.12 plugin runtime, `dify_plugin` 0.2.x, Python standard-library `unittest`

## Global Constraints

- A normal invocation emits exactly one JSON message with all embeddings under `vector`.
- No failure emits a text, JSON, or partial-result message.
- Preserve original exceptions from Dify and embedding providers, including timeout, rate-limit, and connection-limit exceptions.
- Do not add retries, concurrency changes, batch-size changes, or production dependencies.
- Tests must run without a locally installed Dify SDK by replacing only the SDK import and session boundary.

---

### Task 0: Record the Imported Plugin Baseline

**Files:**
- Track: all existing plugin source, metadata, assets, and documentation files that are currently untracked

**Interfaces:**
- Consumes: the unpacked version `0.0.3` plugin copied into this repository
- Produces: a tracked Git baseline against which the error-propagation change can be reviewed

- [ ] **Step 1: Verify the imported source is unchanged**

Run:

```bash
diff -rq /Users/gaoyang/Project/siyu-text_embedding_vector_client_0.0.3 . --exclude=.git --exclude=docs
```

Expected: no output and exit status 0.

- [ ] **Step 2: Commit the imported plugin baseline**

```bash
git add .difyignore .env.example .verification.dify.json GUIDE.md PRIVACY-zh.md PRIVACY.md README-zh.md README.md _assets main.py manifest.yaml provider requirements.txt tools
git commit -m "chore: import text embedding plugin"
```

Expected: one commit containing the unchanged unpacked plugin. Do not push.

---

### Task 1: Enforce Exception-Only Failure Semantics

**Files:**
- Create: `tests/test_embedding_client.py`
- Modify: `tools/embedding-client.py:47-80`

**Interfaces:**
- Consumes: `EmbeddingClient._invoke(tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]`
- Produces: the same `_invoke` signature; one JSON message on success; `ValueError`, `RuntimeError`, or the unchanged provider exception on failure

- [ ] **Step 1: Create the regression test harness and failure-path tests**

Create `tests/test_embedding_client.py` with a lightweight Dify SDK substitute and these tests:

```python
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


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the failure-path tests and verify RED**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests/test_embedding_client.py -v
```

Expected: five failures. The timeout, missing-input, and missing-field tests receive normal messages instead of exceptions; the count-mismatch and empty-result tests receive JSON output instead of exceptions. Import and test discovery must succeed.

- [ ] **Step 3: Add the successful-invocation characterization test**

Add this method to `EmbeddingClientTest` before the `if __name__ == "__main__"` block:

```python
    def test_success_emits_expected_json_message(self):
        response = SimpleNamespace(embeddings=[[0.1, 0.2], [0.3, 0.4]])
        client = self.make_client(lambda **_kwargs: response)

        messages = self.invoke(client, input_text='["first", "second"]')

        self.assertEqual(
            messages,
            [("json", {"vector": [[0.1, 0.2], [0.3, 0.4]]})],
        )
```

- [ ] **Step 4: Run the tests and confirm the success path is already GREEN**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests/test_embedding_client.py -v
```

Expected: the successful-invocation test passes while the five failure-path tests still fail for the reasons recorded in Step 2.

- [ ] **Step 5: Implement minimal exception propagation and response validation**

Replace `EmbeddingClient._invoke` in `tools/embedding-client.py` with:

```python
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
```

- [ ] **Step 6: Run all tests and verify GREEN**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

Expected: six tests pass with no failures or errors.

- [ ] **Step 7: Run source-level verification**

Run:

```bash
python3 -c "import ast, pathlib; files = [pathlib.Path('tools/embedding-client.py'), pathlib.Path('tests/test_embedding_client.py')]; [ast.parse(file.read_text()) for file in files]; print('Parsed 2 Python files successfully')"
git diff --check
git diff -- tools/embedding-client.py tests/test_embedding_client.py
```

Expected: both files parse successfully, `git diff --check` emits no output, and the diff contains only the planned exception handling, response validation, and tests.

- [ ] **Step 8: Commit the tested fix**

```bash
git add tools/embedding-client.py tests/test_embedding_client.py
git commit -m "fix: propagate embedding failures"
```

Expected: one commit containing only the production fix and regression tests. Do not push.
