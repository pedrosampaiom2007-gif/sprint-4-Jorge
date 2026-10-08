"""
Parametros do pipeline RAG. Cada iteracao avaliada em evals/ e um ConfigRAG
diferente, assim o ganho de score fica atribuido a uma mudanca concreta.
"""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass, replace


@dataclass(frozen=True)
class ConfigRAG:
    estrategia_chunking: str = "secao_500"
    k: int = 4
    limiar_relevancia: float = 0.45
    versao_prompt: str = "rag_v3"
    reescrever_pergunta: bool = True
    recusa_sem_contexto: bool = True
    blindagem_documentos: bool = True
    provedor: str = "groq"
    modelo: str = "openai/gpt-oss-20b"
    temperature: float = 0.0
    top_p: float = 1.0
    max_tokens: int = 450

    def com(self, **mudancas) -> "ConfigRAG":
        """Copia da configuracao com alguns campos trocados."""
        return replace(self, **mudancas)

    def como_dict(self) -> dict:
        return asdict(self)


# Iteracao 1: o RAG mais simples possivel — chunk grande, prompt que so manda
# "usar o contexto", sem citacao obrigatoria e sem nenhuma guarda em codigo.
ITERACAO_1 = ConfigRAG(
    estrategia_chunking="fixo_1000",
    k=3,
    limiar_relevancia=0.0,
    versao_prompt="rag_v1",
    reescrever_pergunta=False,
    recusa_sem_contexto=False,
    blindagem_documentos=False,
)

# Iteracao 2: chunk por secao com cabecalho, grounding estrito e citacao no
# prompt, limiar de relevancia e recusa em codigo quando nada relevante volta.
ITERACAO_2 = ConfigRAG(
    estrategia_chunking="secao_500",
    k=4,
    limiar_relevancia=0.45,
    versao_prompt="rag_v2",
    reescrever_pergunta=False,
    recusa_sem_contexto=True,
    blindagem_documentos=True,
)

# Iteracao 3: prompt com exemplos (citacao, recusa, documento em ingles,
# instrucao embutida em documento) e reescrita da pergunta encadeada.
ITERACAO_3 = ConfigRAG(
    estrategia_chunking="secao_500",
    k=4,
    limiar_relevancia=0.45,
    versao_prompt="rag_v3",
    reescrever_pergunta=True,
    recusa_sem_contexto=True,
    blindagem_documentos=True,
)

ITERACOES: dict[str, ConfigRAG] = {
    "iter1": ITERACAO_1,
    "iter2": ITERACAO_2,
    "iter3": ITERACAO_3,
}


def config_padrao() -> ConfigRAG:
    """Configuracao de producao (a ultima iteracao), com overrides do .env."""
    base = ITERACOES[os.environ.get("RAG_ITERACAO", "iter3")]
    mudancas = {}
    if os.environ.get("RAG_PROVEDOR"):
        mudancas["provedor"] = os.environ["RAG_PROVEDOR"].strip()
    if os.environ.get("RAG_MODELO"):
        mudancas["modelo"] = os.environ["RAG_MODELO"].strip()
    if os.environ.get("RAG_K"):
        mudancas["k"] = int(os.environ["RAG_K"])
    return base.com(**mudancas) if mudancas else base
