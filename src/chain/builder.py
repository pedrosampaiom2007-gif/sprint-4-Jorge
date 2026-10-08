"""
builder.py — monta a chain do chatbot.

    prompt | llm | parser | sanitizar

Na Sprint 3 o primeiro elo da chain fazia a busca por palavra-chave. Na Sprint 4
a busca saiu da chain e foi para o Assistente (src/assistente.py), porque ele
precisa dos trechos recuperados depois da resposta: para citar a fonte, para a
interface mostrar de onde veio cada informacao e para o RAGAS medir. A chain
recebe o <contexto> ja montado.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import Runnable, RunnableLambda

from src.llm.provedores import MAX_TOKENS_PADRAO, TEMPERATURA_PADRAO, TOP_P_PADRAO
from src.llm.provedores import construir_llm as _construir_llm_provedor
from src.rag.prompt_rag import TEMPLATE_HUMANO, VERSOES, carregar_prompt_rag
from src.schemas.consulta_recarga import ConsultaRecarga
from src.util_formato import sanitizar_resposta

_RAIZ = Path(__file__).resolve().parent.parent.parent

GROQ_MODEL_PADRAO = os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b")


# ----------------------------------------------------------------- prompt loader
def carregar_prompt(versao: str = "rag_v3") -> str:
    """Prompts da Sprint 4 (rag_v1..v3, em prompts/rag/) ou da Sprint 3 (v1, v2)."""
    if versao in VERSOES:
        return carregar_prompt_rag(versao)
    caminho = _RAIZ / "prompts" / f"system_prompt_{versao}.md"
    texto = caminho.read_text(encoding="utf-8")
    return re.sub(r"<!--.*?-->\s*", "", texto, count=1, flags=re.DOTALL).strip()


# --------------------------------------------------------------------------- LLM
def construir_llm(
    *,
    provedor: str = "groq",
    model: str = GROQ_MODEL_PADRAO,
    temperature: float = TEMPERATURA_PADRAO,
    max_tokens: int = MAX_TOKENS_PADRAO,
    top_p: float = TOP_P_PADRAO,
):
    """Modelo de chat (ver src/llm/provedores.py)."""
    return _construir_llm_provedor(provedor, model, temperature=temperature, top_p=top_p, max_tokens=max_tokens)


# ------------------------------------------------------------------------ prompt
def _montar_chat_prompt(versao_prompt: str) -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages([
        ("system", carregar_prompt(versao_prompt)),
        MessagesPlaceholder("historico", optional=True),  # a memoria injeta aqui
        ("human", TEMPLATE_HUMANO),
    ])


def _garantir_contexto(entrada: dict) -> dict:
    """Quem chama a chain sem contexto (script solto, REPL) recebe o aviso
    explicito em vez de um KeyError."""
    if entrada.get("contexto"):
        return entrada
    return {**entrada, "contexto": "(nenhum trecho relevante encontrado na base)"}


# ------------------------------------------------------------------------ chains
def construir_chain_conversa(*, versao_prompt: str = "rag_v3", **llm_kwargs) -> Runnable:
    """garantir_contexto | prompt | llm | StrOutputParser | sanitizar  ->  str."""
    return (
        RunnableLambda(_garantir_contexto)
        | _montar_chat_prompt(versao_prompt)
        | construir_llm(**llm_kwargs)
        | StrOutputParser()
        | RunnableLambda(sanitizar_resposta)
    )


def construir_chain_estruturada(*, versao_prompt: str = "rag_v3", **llm_kwargs) -> Runnable:
    """garantir_contexto | prompt | llm.with_structured_output(ConsultaRecarga)."""
    return (
        RunnableLambda(_garantir_contexto)
        | _montar_chat_prompt(versao_prompt)
        | construir_llm(**llm_kwargs).with_structured_output(ConsultaRecarga)
    )
