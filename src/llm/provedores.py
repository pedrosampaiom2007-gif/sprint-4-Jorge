"""
Fabrica de modelos de chat. A chain nao sabe qual provedor esta usando: trocar
de modelo e trocar o par (provedor, modelo).

    groq    ChatGroq — openai/gpt-oss-20b (producao) e openai/gpt-oss-120b
    ollama  ChatOllama na Ollama Cloud — gemma4:cloud

Parametros documentados em docs/relatorio_modelos.md.
"""

from __future__ import annotations

import os

TEMPERATURA_PADRAO = 0.0
TOP_P_PADRAO = 1.0
MAX_TOKENS_PADRAO = 450

MODELOS_DISPONIVEIS: list[tuple[str, str]] = [
    ("groq", "openai/gpt-oss-20b"),
    ("groq", "openai/gpt-oss-120b"),
    ("ollama", "gemma4:cloud"),
]


def rotulo(provedor: str, modelo: str) -> str:
    return f"{provedor}:{modelo}"


def construir_llm(
    provedor: str = "groq",
    modelo: str = "openai/gpt-oss-20b",
    *,
    temperature: float = TEMPERATURA_PADRAO,
    top_p: float = TOP_P_PADRAO,
    max_tokens: int = MAX_TOKENS_PADRAO,
):
    """Modelo de chat do provedor pedido, com os mesmos parametros nos dois."""
    if provedor == "groq":
        from langchain_groq import ChatGroq

        extra = {"reasoning_format": "hidden"} if "gpt-oss" in modelo else {}
        return ChatGroq(
            model=modelo,
            temperature=temperature,
            max_tokens=max_tokens,
            model_kwargs={"top_p": top_p},
            max_retries=2,  # limite por minuto e tratado em evals/; cota diaria nao adianta esperar
            **extra,
        )
    if provedor == "ollama":
        from langchain_ollama import ChatOllama

        chave = os.environ.get("OLLAMA_API_KEY", "").strip()
        kwargs = {"client_kwargs": {"headers": {"Authorization": f"Bearer {chave}"}}} if chave else {}
        return ChatOllama(
            model=modelo,
            base_url=os.environ.get("OLLAMA_BASE_URL", "https://ollama.com").strip(),
            temperature=temperature,
            top_p=top_p,
            num_predict=max_tokens,
            **kwargs,
        )
    raise ValueError(f"provedor desconhecido: {provedor} (use 'groq' ou 'ollama')")


def chaves_faltando(provedores: set[str]) -> list[str]:
    """Variaveis de ambiente que faltam para os provedores pedidos."""
    faltam = []
    if "groq" in provedores and not os.environ.get("GROQ_API_KEY", "").strip():
        faltam.append("GROQ_API_KEY")
    if "ollama" in provedores and not os.environ.get("OLLAMA_API_KEY", "").strip():
        faltam.append("OLLAMA_API_KEY")
    return faltam
