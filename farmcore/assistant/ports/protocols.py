from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class ModelInfo:
    provider: str
    model_id: str
    revision: str
    dimension: int | None = None


@dataclass(frozen=True)
class EntailmentResult:
    entails: bool
    score: float


@dataclass(frozen=True)
class ExtractionResult:
    text: str
    page_count: int
    is_empty: bool


@dataclass(frozen=True)
class TableResult:
    caption: str
    rows: list[list[str]]


@dataclass(frozen=True)
class StoredObject:
    key: str
    size_bytes: int
    content_type: str


@dataclass(frozen=True)
class Candidate:
    chunk_id: str
    text: str
    score: float


@dataclass(frozen=True)
class ScoredCandidate:
    chunk_id: str
    text: str
    score: float


class EmbeddingPort(Protocol):
    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...
    def embed_query(self, text: str) -> list[float]: ...
    def model_info(self) -> ModelInfo: ...


class GenerationPort(Protocol):
    def generate(self, prompt: str, *, system: str | None = None, max_tokens: int = 1024) -> str: ...
    def generate_structured(self, prompt: str, schema: type[T], *, system: str | None = None) -> T: ...
    def model_info(self) -> ModelInfo: ...


class RerankPort(Protocol):
    def rerank(self, query: str, candidates: list[Candidate]) -> list[ScoredCandidate]: ...
    def model_info(self) -> ModelInfo: ...
    def healthcheck(self) -> bool: ...


class EntailmentPort(Protocol):
    def entails(self, claim: str, evidence: str) -> EntailmentResult: ...
    def entails_batch(self, pairs: list[tuple[str, str]]) -> list[EntailmentResult]: ...
    def model_info(self) -> ModelInfo: ...


class ExtractionPort(Protocol):
    def extract_text(self, file_bytes: bytes, mime: str) -> ExtractionResult: ...
    def extract_tables(self, file_bytes: bytes, mime: str) -> list[TableResult]: ...
    def tool_info(self) -> ModelInfo: ...


class ObjectStorePort(Protocol):
    def put(self, key: str, data: bytes, *, content_type: str) -> StoredObject: ...
    def get(self, key: str) -> bytes: ...
    def presign(self, key: str, *, expires_seconds: int = 3600) -> str: ...
