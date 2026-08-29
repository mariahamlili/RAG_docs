from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VersionTuple:
    corpus_snapshot_id: str
    chunker_version: str
    embedding_model_id: str
    retrieval_config_version: str
    reranker_model_id: str
    prompt_template_id: str
    tool_registry_version: str
    generation_model_id: str
    verifier_model_id: str
    schema_version: str

    def to_dict(self) -> dict[str, str]:
        return {
            "corpus_snapshot_id": self.corpus_snapshot_id,
            "chunker_version": self.chunker_version,
            "embedding_model_id": self.embedding_model_id,
            "retrieval_config_version": self.retrieval_config_version,
            "reranker_model_id": self.reranker_model_id,
            "prompt_template_id": self.prompt_template_id,
            "tool_registry_version": self.tool_registry_version,
            "generation_model_id": self.generation_model_id,
            "verifier_model_id": self.verifier_model_id,
            "schema_version": self.schema_version,
        }

    def fingerprint(self) -> str:
        return f"{self.corpus_snapshot_id}-{self.retrieval_config_version}-{self.tool_registry_version}"


def version_tuple_from_settings(settings_dict: dict[str, str]) -> VersionTuple:
    return VersionTuple(**settings_dict)
