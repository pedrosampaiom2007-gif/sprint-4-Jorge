"""
ChromaDB persistente (data/chroma/), uma colecao por estrategia de chunking.

Reindexar so acontece quando o conjunto de chunks muda: os ids sao estaveis
(doc:secao:n), entao rodar a indexacao de novo sem mexer na base nao gasta
nenhuma chamada de embedding.
"""

from __future__ import annotations

from pathlib import Path

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from src.rag.chunking import dividir
from src.rag.loader import RAIZ, carregar_base

PASTA_CHROMA = RAIZ / "data" / "chroma"
PREFIXO_COLECAO = "chargegrid_kb"
TAMANHO_LOTE = 32

_CACHE: dict[tuple[str, str], object] = {}


def nome_colecao(estrategia: str) -> str:
    return f"{PREFIXO_COLECAO}_{estrategia}"


def abrir(estrategia: str, embeddings: Embeddings | None = None, pasta: Path | None = None):
    """langchain_chroma.Chroma da estrategia (cria a colecao vazia se nao existir)."""
    from langchain_chroma import Chroma

    pasta = pasta or PASTA_CHROMA
    chave = (str(pasta), estrategia)
    if chave not in _CACHE:
        if embeddings is None:
            from src.rag.embeddings import criar_embeddings

            embeddings = criar_embeddings()
        _CACHE[chave] = Chroma(
            collection_name=nome_colecao(estrategia),
            embedding_function=embeddings,
            persist_directory=str(pasta),
            collection_metadata={"hnsw:space": "cosine"},
        )
    return _CACHE[chave]


def _metadados_chroma(meta: dict) -> dict:
    return {k: v for k, v in meta.items() if isinstance(v, (str, int, float, bool))}


def indexar(
    estrategia: str,
    documentos: list[Document] | None = None,
    embeddings: Embeddings | None = None,
    recriar: bool = False,
    pasta: Path | None = None,
) -> dict:
    """Carrega, divide, gera embeddings e grava. Devolve um resumo da indexacao."""
    documentos = documentos if documentos is not None else carregar_base()
    chunks = dividir(documentos, estrategia)
    ids = [c.metadata["chunk_id"] for c in chunks]
    loja = abrir(estrategia, embeddings, pasta)

    existentes = set(loja.get(include=[])["ids"])
    if not recriar and existentes == set(ids):
        return {"colecao": nome_colecao(estrategia), "chunks": len(ids), "indexados_agora": 0}

    if existentes:
        loja.delete(ids=list(existentes))
    for inicio in range(0, len(chunks), TAMANHO_LOTE):
        lote = chunks[inicio:inicio + TAMANHO_LOTE]
        loja.add_texts(
            texts=[c.page_content for c in lote],
            metadatas=[_metadados_chroma(c.metadata) for c in lote],
            ids=[c.metadata["chunk_id"] for c in lote],
        )
    return {"colecao": nome_colecao(estrategia), "chunks": len(ids), "indexados_agora": len(ids)}


def total(estrategia: str, pasta: Path | None = None) -> int:
    return len(abrir(estrategia, pasta=pasta).get(include=[])["ids"])


if __name__ == "__main__":
    # python -m src.rag.vector_store  — indexa as duas estrategias
    from dotenv import load_dotenv

    load_dotenv()
    from src.rag.chunking import ESTRATEGIAS

    for nome in ESTRATEGIAS:
        print(indexar(nome))
