# Propagate Embedding Errors

## Problem

The embedding tool currently catches every exception raised while invoking the selected embedding model and converts it into a normal text message. Dify therefore treats timeouts, rate limits, connection-limit failures, and other model errors as successful tool output. Downstream nodes may then consume the error text instead of an embedding vector.

The tool also returns normal text messages when required input is missing or when the model response does not contain embeddings. These conditions must be failures because the tool cannot produce its declared output.

## Desired Behavior

The tool has exactly two outcomes:

1. It returns a JSON message containing valid embedding results under `vector`.
2. It raises an exception, causing Dify to mark the node as failed and route execution according to the workflow's configured failure handling.

No failure may be represented as a normal text message.

## Design

Keep the existing input parsing, batching, model selection, and successful JSON output unchanged.

- Remove the broad `try`/`except Exception` block so model and SDK exceptions retain their original type, message, and traceback.
- Raise `ValueError` when `input_text` is missing.
- Raise `RuntimeError` when a model response has no `embeddings` field.
- Raise `RuntimeError` when a batch returns a different number of embeddings than the number of input texts in that batch.
- Raise `RuntimeError` when processing completes without any embeddings.

The plugin will not retry calls, change concurrency, change batch sizing, or add dependencies. Retry and fallback behavior remain workflow or model-provider concerns.

## Data Flow

For each invocation, the tool validates the input, parses it into a text list, divides the list into batches, and invokes the configured embedding model for each batch. Each response is validated before its embeddings are appended. Only after every batch succeeds does the tool emit the JSON result.

If validation or any model call fails, execution exits immediately through an exception. No partial vector result or error text is emitted.

## Testing

Add focused unit tests using Python's standard `unittest` framework so no production dependency is introduced. Stub only the Dify SDK boundary that cannot be exercised locally.

Tests will verify:

- A model invocation exception is re-raised as the same exception rather than converted to a text message.
- Missing input raises `ValueError`.
- A response without embeddings raises `RuntimeError`.
- A batch result count mismatch raises `RuntimeError`.
- Empty results raise `RuntimeError`.
- A successful invocation still emits exactly one JSON message containing the expected vectors.

The regression test for swallowed model errors must be observed failing before the production code is changed, then all tests must pass after the minimal implementation.
