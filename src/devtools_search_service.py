"""Typed HTTP surface for scanned developer-tool documents."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .infrai_document_pipeline import DocumentPipeline, InfraiError, build_pipeline


class IndexDocumentRequest(BaseModel):
    document_id: str = Field(min_length=1)
    pdf: str = Field(min_length=1)
    collection: str = Field(min_length=1)


class SearchDocumentRequest(BaseModel):
    question: str = Field(min_length=1)
    collection: str = Field(min_length=1)
    top_k: int = Field(default=3, ge=1, le=10)


app = FastAPI(title="Developer document OCR search")


@lru_cache
def pipeline() -> DocumentPipeline:
    return build_pipeline()


def client_error(error: InfraiError) -> HTTPException:
    status = error.status_code if 400 <= error.status_code < 500 else 502
    return HTTPException(status_code=status, detail={"code": error.code})


@app.post("/documents/index")
def index_document(request: IndexDocumentRequest) -> dict[str, str]:
    try:
        indexed = pipeline().index_document(request.document_id, request.pdf, request.collection)
    except InfraiError as error:
        raise client_error(error) from error
    return {"document_id": indexed.document_id, "collection": indexed.collection}


@app.post("/documents/search")
def search_document(request: SearchDocumentRequest) -> dict[str, Any]:
    try:
        hits = pipeline().search(request.question, request.collection, request.top_k)
    except InfraiError as error:
        raise client_error(error) from error
    return {"hits": hits}
