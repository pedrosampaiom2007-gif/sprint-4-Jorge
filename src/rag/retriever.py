"""
Recuperacao de trechos: busca vetorial no Chroma + filtro de acesso + limiar
de relevancia + blindagem, e (opcional) reescrita da pergunta encadeada.

O filtro de acesso usa o metadado `acesso` de cada documento: sem perfil de
gestao, a busca so enxerga documentos publicos — o relatorio comercial SP2
nem entra no ranking, entao nao tem como vazar.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever

from src.rag.blindagem import blindar
from src.rag.config import ConfigRAG
from src.rag.vector_store import abrir


@dataclass
class Trecho:
    texto: str
    metadados: dict
    score: float
    suspeito: bool = False
    extras: dict = field(default_factory=dict)

    @property
    def titulo(self) -> str:
        return str(self.metadados.get("titulo", "documento"))

    @property
    def secao(self) -> str:
        return str(self.metadados.get("secao", ""))

    @property
    def doc_id(self) -> str:
        return str(self.metadados.get("doc_id", ""))

    @property
    def chunk_id(self) -> str:
        return str(self.metadados.get("chunk_id", ""))

    def citacao(self) -> str:
        """Ex.: "Tabela tarifaria do ChargeGrid › Horario de ponta"."""
        return f"{self.titulo} › {self.secao}" if self.secao else self.titulo

    def como_dict(self) -> dict:
        return {
            "citacao": self.citacao(), "doc_id": self.doc_id, "chunk_id": self.chunk_id,
            "score": self.score, "suspeito": self.suspeito, "url": self.metadados.get("url", ""),
            "texto": self.texto,
        }


def filtro_acesso(acesso_gestao: bool) -> dict | None:
    return None if acesso_gestao else {"acesso": "publico"}


def recuperar(pergunta: str, cfg: ConfigRAG, acesso_gestao: bool = False, loja=None) -> list[Trecho]:
    """Os k trechos mais relevantes acima do limiar, ja blindados."""
    loja = loja or abrir(cfg.estrategia_chunking)
    resultados = loja.similarity_search_with_relevance_scores(
        pergunta, k=cfg.k, filter=filtro_acesso(acesso_gestao)
    )
    trechos = []
    for doc, score in resultados:
        if score < cfg.limiar_relevancia:
            continue
        texto, removidas = blindar(doc.page_content) if cfg.blindagem_documentos else (doc.page_content, 0)
        trechos.append(Trecho(texto=texto, metadados=dict(doc.metadata), score=round(float(score), 4),
                              suspeito=removidas > 0))
    return trechos


# ---------------------------------------------------------- pergunta encadeada
_ANAFORICA = re.compile(
    r"^\s*(e\b|e o|e a|e os|e as|e no|e na|e se|mas e|tambem|isso|esse|essa|este|esta|dele|dela|nele|nela|"
    r"o segundo|a segunda|o primeiro|o outro|a outra|quanto custa isso)",
    re.IGNORECASE,
)

_PROMPT_REESCRITA = (
    "Reescreva a ULTIMA pergunta do usuario como uma pergunta completa e independente, "
    "trocando pronomes e referencias pelo assunto que aparece no historico. "
    "Responda somente com a pergunta reescrita, em portugues, sem explicar nada.\n\n"
    "Historico:\n{historico}\n\nUltima pergunta: {pergunta}"
)


def precisa_reescrever(pergunta: str, historico: list) -> bool:
    if not historico:
        return False
    palavras = len(pergunta.split())
    return palavras <= 6 or bool(_ANAFORICA.match(pergunta))


def reescrever_pergunta(pergunta: str, historico: list, llm) -> str:
    """Pergunta de continuacao ("e no horario de ponta?") vira pergunta completa
    antes da busca. Sem isso a busca vetorial nao sabe do que se fala."""
    if not precisa_reescrever(pergunta, historico):
        return pergunta
    linhas = []
    for msg in historico[-6:]:
        papel = "Usuario" if getattr(msg, "type", "") == "human" else "Assistente"
        linhas.append(f"{papel}: {str(msg.content)[:400]}")
    try:
        nova = llm.invoke(_PROMPT_REESCRITA.format(historico="\n".join(linhas), pergunta=pergunta))
        texto = str(getattr(nova, "content", nova)).strip().strip('"')
        return texto if 3 <= len(texto) <= 300 else pergunta
    except Exception:  # noqa: BLE001
        return pergunta


class RetrieverChargeGrid(BaseRetriever):
    """O mesmo `recuperar` como BaseRetriever do LangChain, para usar numa chain LCEL."""

    cfg: ConfigRAG
    acesso_gestao: bool = False

    def _get_relevant_documents(self, query: str, *, run_manager: CallbackManagerForRetrieverRun) -> list[Document]:
        return [
            Document(page_content=t.texto, metadata={**t.metadados, "score": t.score, "citacao": t.citacao()})
            for t in recuperar(query, self.cfg, self.acesso_gestao)
        ]
