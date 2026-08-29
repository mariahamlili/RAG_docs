from assistant.ports.noop import default_ports
from assistant.ports.protocols import (
    EmbeddingPort,
    EntailmentPort,
    ExtractionPort,
    GenerationPort,
    ObjectStorePort,
    RerankPort,
)

_PORTS = default_ports()


def get_embedding_port() -> EmbeddingPort:
    return _PORTS["embedding"]  # type: ignore[return-value]


def get_generation_port() -> GenerationPort:
    return _PORTS["generation"]  # type: ignore[return-value]


def get_rerank_port() -> RerankPort:
    return _PORTS["rerank"]  # type: ignore[return-value]


def get_entailment_port() -> EntailmentPort:
    return _PORTS["entailment"]  # type: ignore[return-value]


def get_extraction_port() -> ExtractionPort:
    return _PORTS["extraction"]  # type: ignore[return-value]


def get_object_store_port() -> ObjectStorePort:
    return _PORTS["object_store"]  # type: ignore[return-value]
