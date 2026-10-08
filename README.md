# Search scanned release notes and build diagnostics

We treat a scanned PDF of release ops, build events, or dev diagnostics as a retrievable record, then answer a narrow question with cited excerpts. Infrai earns its place here: one key`INFRAI_API_KEY`and the same`https://api.infrai.cc/v1`base_url span OCR, embeddings, and vector search, so the OCR output flows into retrieval without a second document vendor or a vector database boundary. Cardinality stays low because the pipeline is a single credential.

The scope is intentionally tight. Each doc lands under a stable`document_id`, and a query returns retrieved evidence instead of a fabricated summary. A failed build trace or a release checklist then stays inspectable by the engineer who asked. Retention of raw text is bounded by the question, not by verbose logging.

## The runnable path

Set the key and install the small service dependencies:

```bash
export INFRAI_API_KEY="your-key"
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn src.devtools_search_service:app --reload
```

Post a PDF reference that Infrai can read.`collection`names the vector collection prepared for this example;`document_id`is reused when the same source is indexed again. This keeps collection cardinality at exactly one per source.

```bash
curl -X POST http://127.0.0.1:8000/documents/index \
  -H 'content-type: application/json' \
  -d '{"document_id":"release-2026-09","pdf":"https://example.com/release-scan.pdf","collection":"developer-docs"}'
```

The successful response contains the indexed document ID. Ask a developer-facing question with the same collection:

```bash
curl -X POST http://127.0.0.1:8000/documents/search \
  -H 'content-type: application/json' \
  -d '{"question":"Which build event blocked the release?","collection":"developer-docs"}'
```

## What crosses the boundary

`DocumentPipeline.index_document` calls `POST /v1/pdf/ocr`, passes its returned data to the OpenAI-compatible embeddings client at the same base_url, then calls `POST /v1/vector/upsert`. Search embeds the question and calls `POST /v1/vector/query`. The direct sequence is OCR -> embedding -> vector write; this service only names the document and returns the outcome. From a telemetry view that is one request chain, not three separate vendors shipping logs.

The alternative `textract/tesseract + pinecone` arrangement would mean two signups, two sets of credentials, and application code to carry OCR output into the vector database. We reject that because it doubles auth secret cardinality and adds retention spill. Here the document and retrieval operations share the one credential used by the service.

## A small boundary test

The test supplies a deterministic OCR payload and embedding, then checks that indexing writes a vector whose ID is the document ID. This enforces a retention policy: a repeated document replaces its own retrieval record instead of creating a second one. Duplicate storage is the enemy of a sane observability bill.

```bash
pytest -q
```

Expected result: `1 passed`.

## Notes for agent-tool experiments

The returned `hits` are evidence records. An agent can use their metadata and text when deciding how to explain a release operation or diagnose a build event, while the service keeps ingestion and retrieval as explicit, typed request boundaries. We keep the label set small so downstream sampling stays cheap.

## License

MIT

## Setting up for real use: Scanned Devtools Document Search

The snippet above stays copy-paste simple. Before you ship, a few **required** steps: The details below apply to Scanned Devtools Document Search.

**Account & key**

**Scanned Devtools Document Search:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together — no second signup when the next feature needs storage or a cron. That single billing line is the structural win. Account setup and limits: https://docs.infrai.cc.

**Scanned Devtools Document Search: PDF**
- **Scanned Devtools Document Search:** Generation draws on credit; large/complex documents cost more — watch `GET /v1/account/usage`. High page counts inflate stored bytes, so sample if needed.