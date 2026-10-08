"""
Estrategias de chunking comparadas na avaliacao.

    fixo_1000   RecursiveCharacterTextSplitter 1000/150 sobre o texto cru.
                Chunk grande: cabe mais contexto, mas mistura assuntos e a
                similaridade fica diluida.
    secao_500   500/75 dentro de cada pagina ou secao, e cada chunk comeca com
                "titulo do documento — secao". O cabecalho ajuda a busca a achar
                o trecho certo e da a citacao de graca.

Overlap de 15% nas duas, para a frase cortada no limite aparecer inteira em
algum dos dois chunks vizinhos.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

SEPARADORES = ["\n\n", "\n", ". ", " ", ""]
MIN_CARACTERES = 40


@dataclass(frozen=True)
class EstrategiaChunking:
    nome: str
    chunk_size: int
    chunk_overlap: int
    com_cabecalho: bool


ESTRATEGIAS: dict[str, EstrategiaChunking] = {
    "fixo_1000": EstrategiaChunking("fixo_1000", 1000, 150, com_cabecalho=False),
    "secao_500": EstrategiaChunking("secao_500", 500, 75, com_cabecalho=True),
}


def _slug(texto: str) -> str:
    t = unicodedata.normalize("NFKD", texto.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:40] or "s"


def dividir(documentos: list[Document], estrategia: str) -> list[Document]:
    """Divide os documentos e da a cada chunk um id estavel (doc:secao:n)."""
    cfg = ESTRATEGIAS[estrategia]
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=cfg.chunk_size,
        chunk_overlap=cfg.chunk_overlap,
        separators=SEPARADORES,
        keep_separator=True,
    )
    chunks: list[Document] = []
    contagem: dict[str, int] = {}
    for doc in documentos:
        for parte in splitter.split_text(doc.page_content):
            parte = parte.strip()
            if len(parte) < MIN_CARACTERES:
                continue
            chave = f"{doc.metadata['doc_id']}:{_slug(doc.metadata['secao'])}"
            contagem[chave] = contagem.get(chave, 0) + 1
            texto = (
                f"{doc.metadata['titulo']} — {doc.metadata['secao']}\n{parte}"
                if cfg.com_cabecalho else parte
            )
            chunks.append(Document(
                page_content=texto,
                metadata={**doc.metadata, "chunk_id": f"{chave}:{contagem[chave]}", "estrategia": estrategia},
            ))
    return chunks


def estatisticas(chunks: list[Document]) -> dict:
    tamanhos = [len(c.page_content) for c in chunks] or [0]
    return {
        "chunks": len(chunks),
        "media_caracteres": round(sum(tamanhos) / len(tamanhos), 1),
        "min_caracteres": min(tamanhos),
        "max_caracteres": max(tamanhos),
    }
