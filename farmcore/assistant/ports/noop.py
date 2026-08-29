from __future__ import annotations

from assistant.ports.protocols import (
    Candidate,
    EmbeddingPort,
    EntailmentPort,
    EntailmentResult,
    ExtractionPort,
    ExtractionResult,
    GenerationPort,
    ModelInfo,
    ObjectStorePort,
    RerankPort,
    ScoredCandidate,
    StoredObject,
    TableResult,
)


class NoOpEmbeddingPort:
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * 8 for _ in texts]

    def embed_query(self, text: str) -> list[float]:
        return [0.0] * 8

    def model_info(self) -> ModelInfo:
        return ModelInfo(provider="noop", model_id="embedding-stub", revision="0", dimension=8)


class NoOpGenerationPort:
    def generate(self, prompt: str, *, system: str | None = None, max_tokens: int = 1024) -> str:
        return "stub"

    def generate_structured(self, prompt, schema, *, system: str | None = None):
        raise NotImplementedError("structured generation not available in stub")

    def model_info(self) -> ModelInfo:
        return ModelInfo(provider="noop", model_id="generation-stub", revision="0")


class NoOpRerankPort:
    def rerank(self, query: str, candidates: list[Candidate]) -> list[ScoredCandidate]:
        return [ScoredCandidate(c.chunk_id, c.text, c.score) for c in candidates]

    def model_info(self) -> ModelInfo:
        return ModelInfo(provider="noop", model_id="rerank-stub", revision="0")

    def healthcheck(self) -> bool:
        return True


class NoOpEntailmentPort:
    def entails(self, claim: str, evidence: str) -> EntailmentResult:
        return EntailmentResult(entails=True, score=1.0)

    def entails_batch(self, pairs: list[tuple[str, str]]) -> list[EntailmentResult]:
        return [EntailmentResult(entails=True, score=1.0) for _ in pairs]

    def model_info(self) -> ModelInfo:
        return ModelInfo(provider="noop", model_id="entailment-stub", revision="0")


class NoOpExtractionPort:
    def extract_text(self, file_bytes: bytes, mime: str) -> ExtractionResult:
        return ExtractionResult(text="", page_count=0, is_empty=True)

    def extract_tables(self, file_bytes: bytes, mime: str) -> list[TableResult]:
        return []

    def tool_info(self) -> ModelInfo:
        return ModelInfo(provider="noop", model_id="extraction-stub", revision="0")


class NoOpObjectStorePort:
    def put(self, key: str, data: bytes, *, content_type: str) -> StoredObject:
        return StoredObject(key=key, size_bytes=len(data), content_type=content_type)

    def get(self, key: str) -> bytes:
        return b""

    def presign(self, key: str, *, expires_seconds: int = 3600) -> str:
        return f"http://localhost:9000/{key}?expires={expires_seconds}"


def default_ports() -> dict[str, object]:
    return {
        "embedding": NoOpEmbeddingPort(),
        "generation": NoOpGenerationPort(),
        "rerank": NoOpRerankPort(),
        "entailment": NoOpEntailmentPort(),
        "extraction": NoOpExtractionPort(),
        "object_store": NoOpObjectStorePort(),
    }
