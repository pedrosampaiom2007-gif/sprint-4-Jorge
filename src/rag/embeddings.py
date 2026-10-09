"""
Embeddings com nomic-embed-text via Ollama (Ollama Cloud por padrao).

O nomic-embed-text foi treinado com prefixo de tarefa: "search_document: " no
que vai para o indice e "search_query: " na pergunta. Sem os prefixos a
similaridade entre pergunta e trecho cai visivelmente.
"""

from __future__ import annotations

import os

from langchain_core.embeddings import Embeddings

MODELO_EMBEDDING = "nomic-embed-text"
PREFIXO_DOCUMENTO = "search_document: "
PREFIXO_CONSULTA = "search_query: "


class NomicEmbeddings(Embeddings):
    """Envolve um Embeddings qualquer aplicando os prefixos do nomic."""

    def __init__(self, base: Embeddings) -> None:
        self.base = base

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.base.embed_documents([PREFIXO_DOCUMENTO + t for t in texts])

    def embed_query(self, text: str) -> list[float]:
        return self.base.embed_query(PREFIXO_CONSULTA + text)


def endpoint_embeddings() -> str:
    """Servidor Ollama que gera os embeddings (gravado junto dos resultados)."""
    return os.environ.get("OLLAMA_EMBED_BASE_URL", "").strip() or os.environ.get(
        "OLLAMA_BASE_URL", "https://ollama.com"
    ).strip()


def criar_embeddings() -> NomicEmbeddings:
    """OllamaEmbeddings(model='nomic-embed-text').

    OLLAMA_EMBED_BASE_URL escolhe o endpoint: vazio usa a Ollama Cloud com a
    OLLAMA_API_KEY; http://localhost:11434 usa o Ollama instalado na maquina.
    """
    from langchain_ollama import OllamaEmbeddings

    base_url = endpoint_embeddings()
    chave = os.environ.get("OLLAMA_API_KEY", "").strip()
    kwargs = {"client_kwargs": {"headers": {"Authorization": f"Bearer {chave}"}}} if chave else {}
    return NomicEmbeddings(OllamaEmbeddings(model=MODELO_EMBEDDING, base_url=base_url, **kwargs))
