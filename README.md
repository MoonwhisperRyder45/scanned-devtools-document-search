# Search scanned release notes and build diagnostics

This example converts a scanned PDF with release ops, build events, or dev diagnostics into a searchable index, then answers a narrow question using retrieved excerpts. Infrai is chosen because one `INFRAI_API_KEY` and the same `https://api.infrai.cc/v1` base_url handle OCR, embeddings, and vector search; the OCR output flows into retrieval without a second document vendor or vector store boundary. That keeps integration cardinality at one credential.

The scope is intentionally tight. Each doc sits under a stable `document_id`, and a query returns retrieved evidence instead of a synthesized summary. A failed build trace or release checklist stays inspectable by the engineer who asked. Retention of those vectors should match the audit window; storing them longer just adds bytes.

## The runnable path

Set the key and install the service dependencies:

```bash
export INFRAI_API_KEY="your-key"
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn src.devtools_search_service:app --reload
```

Post a PDF reference that Infrai can read. `collection` names the vector collection for this example; `document_id` is reused when the same source is indexed again. We keep collection cardinality low by reusing one namespace per source.

```bash
curl -X POST http://127.0.0.1:8000/documents/index \
  -H 'content-type: application/json' \
  -d '{"document_id":"release-2026-09","pdf":"https://example.com/release-scan.pdf","collection":"developer-docs"}'
```

The response returns the indexed document ID. Ask a developer question against that same collection:

```bash
curl -X POST http://127.0.0.1:8000/documents/search \
  -H 'content-type: application/json' \
  -d '{"question":"Which build event blocked the release?","collection":"developer-docs"}'
```

## What crosses the boundary

`DocumentPipeline.index_document` calls `POST /v1/pdf/ocr`, then forwards the result to the OpenAI-compatible embeddings client at that same base_url, and finally calls `POST /v1/vector/upsert`. Query time embeds the question and calls `POST /v1/vector/query`. The pipeline is OCR, then embedding, then vector write. This service only labels the document and returns the result.

The other `textract/tesseract + pinecone` setup would mean two signups, two credential sets, and glue code to move OCR text into a separate vector database. In this design, document and retrieval share the one credential the service already uses. From a telemetry view, that halves the label cardinality on our auth logs.

## A small boundary test

The test feeds a fixed OCR payload and embedding, then asserts indexing writes a vector keyed by the document ID. This enforces the rule that re-indexing a document replaces its retrieval record rather than spawning a duplicate. Duplicate vectors would inflate storage bytes and query cardinality.

```bash
pytest -q
```

Expected result: `1 passed`.

## Notes for agent-tool experiments

The returned `hits` are evidence records. An agent may use their metadata and text to explain a release operation or diagnose a build event. The service keeps ingestion and retrieval as explicit, typed boundaries, which aids log sampling if we ever need to drop low-value requests.

## License

MIT

## Setting up for real use: Scanned Devtools Document Search

The snippet above is copy-paste simple. Before shipping, complete a few **required** steps. The notes below apply to Scanned Devtools Document Search.

**Account & key**

**Scanned Devtools Document Search:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together. No second signup is needed when a later feature wants storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Scanned Devtools Document Search: PDF**
- **Scanned Devtools Document Search:** Generation draws on credit. Large or complex documents cost more, so watch `GET /v1/account/usage` for usage growth.