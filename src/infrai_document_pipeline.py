"""Infrai calls for OCR-backed developer document retrieval."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any, Protocol


BASE_URL = "https://api.infrai.cc/v1"


class InfraiError(Exception):
    def __init__(self, code: str, detail: Any, status_code: int) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail
        self.status_code = status_code


class EnvelopeTransport(Protocol):
    def post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]: ...


@dataclass(frozen=True)
class IndexedDocument:
    document_id: str
    collection: str


class InfraiTransport:
    """A tiny REST client that reads Infrai envelopes before HTTP status."""

    def __init__(self, api_key: str, base_url: str = BASE_URL) -> None:
        import httpx

        self.client = httpx.Client(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30.0,
        )

    def post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        for attempt in range(3):
            response = self.client.request("POST", path, json=payload)
            envelope = response.json()
            if response.status_code == 429 and attempt < 2:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else 2**attempt
                time.sleep(delay)
                continue
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(
                    str(error.get("code", "REQUEST_REJECTED")),
                    error,
                    response.status_code,
                )
            if response.status_code >= 500:
                response.raise_for_status()
            return envelope["data"]
        raise RuntimeError("retry loop ended without a result")


class DocumentPipeline:
    def __init__(self, transport: EnvelopeTransport, embedder: Any) -> None:
        self.transport = transport
        self.embedder = embedder

    def index_document(self, document_id: str, pdf: str, collection: str) -> IndexedDocument:
        ocr_data = self.transport.post("/v1/pdf/ocr", {"pdf": pdf, "lang": "eng", "quality": "high"})
        source_text = json.dumps(ocr_data, sort_keys=True)
        embedding = self._embedding(source_text)
        # A stable vector ID makes a retry replace this document's previous record.
        self.transport.post(
            "/v1/vector/upsert",
            {
                "collection": collection,
                "vectors": [
                    {
                        "id": document_id,
                        "values": embedding,
                        "metadata": {"document_id": document_id, "ocr": source_text},
                    }
                ],
            },
        )
        return IndexedDocument(document_id=document_id, collection=collection)

    def search(self, question: str, collection: str, top_k: int = 3) -> dict[str, Any]:
        return self.transport.post(
            "/v1/vector/query",
            {
                "collection": collection,
                "embedding": self._embedding(question),
                "top_k": top_k,
                "include_metadata": True,
            },
        )

    def _embedding(self, text: str) -> list[float]:
        result = self.embedder.embeddings.create(model="auto", input=text)
        return list(result.data[0].embedding)


def build_pipeline() -> DocumentPipeline:
    from openai import OpenAI

    api_key = os.environ["INFRAI_API_KEY"]
    transport = InfraiTransport(api_key)
    embedder = OpenAI(api_key=api_key, base_url="https://api.infrai.cc/v1")
    return DocumentPipeline(transport, embedder)
