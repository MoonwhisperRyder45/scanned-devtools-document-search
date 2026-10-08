import sys
from pathlib import Path
from types import SimpleNamespace

# Keep the runnable example importable without packaging it before the test.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.infrai_document_pipeline import DocumentPipeline


class FakeTransport:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def post(self, path: str, payload: dict) -> dict:
        self.calls.append((path, payload))
        if path == "/v1/pdf/ocr":
            return {"pages": [{"text": "build 184 blocked release 9"}]}
        return {"written": 1}


class FakeEmbeddings:
    def create(self, model: str, input: str) -> SimpleNamespace:
        assert model == "auto"
        assert "build 184" in input
        return SimpleNamespace(data=[SimpleNamespace(embedding=[0.1, 0.2])])


class FakeEmbedder:
    embeddings = FakeEmbeddings()


def test_reindexing_uses_the_document_id_as_the_vector_id() -> None:
    transport = FakeTransport()
    pipeline = DocumentPipeline(transport, FakeEmbedder())

    indexed = pipeline.index_document("release-9", "https://example.com/scan.pdf", "developer-docs")

    assert indexed.document_id == "release-9"
    assert transport.calls[1][0] == "/v1/vector/upsert"
    assert transport.calls[1][1]["vectors"][0]["id"] == "release-9"
