"""
Chamada multi-provider: a mesma pergunta, com os mesmos trechos recuperados,
respondida por mais de um modelo e mais de uma versao de prompt, em paralelo.

A busca roda uma vez so: assim a diferenca entre as respostas e do modelo e do
prompt, nao da recuperacao.
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from src.guardrails.moderation import RESPOSTA_PADRAO, detectar_injection, resposta_parece_vazamento
from src.llm.provedores import construir_llm, rotulo
from src.rag.citacao import garantir_citacao
from src.rag.config import ConfigRAG, config_padrao
from src.rag.prompt_rag import RESPOSTA_SEM_CONTEXTO, TEMPLATE_HUMANO, carregar_prompt_rag, montar_contexto
from src.rag.retriever import recuperar
from src.util_formato import sanitizar_resposta

COMBINACOES_PADRAO: list[tuple[str, str, str]] = [
    ("groq", "openai/gpt-oss-20b", "rag_v3"),
    ("groq", "openai/gpt-oss-20b", "rag_v2"),
    ("ollama", "gemma4:cloud", "rag_v3"),
]


@dataclass
class RespostaModelo:
    provedor: str
    modelo: str
    versao_prompt: str
    resposta: str
    latencia_s: float
    erro: str | None = None

    @property
    def rotulo(self) -> str:
        return f"{rotulo(self.provedor, self.modelo)} · {self.versao_prompt}"


def _responder(provedor: str, modelo: str, versao: str, pergunta: str, contexto: str,
               trechos: list, cfg: ConfigRAG) -> RespostaModelo:
    inicio = time.perf_counter()
    try:
        prompt = ChatPromptTemplate.from_messages([
            ("system", carregar_prompt_rag(versao)),
            ("human", TEMPLATE_HUMANO),
        ])
        llm = construir_llm(provedor, modelo, temperature=cfg.temperature, top_p=cfg.top_p,
                            max_tokens=cfg.max_tokens)
        texto = (prompt | llm | StrOutputParser()).invoke({"pergunta": pergunta, "contexto": contexto})
        texto = sanitizar_resposta(texto)
        if resposta_parece_vazamento(texto):
            texto = RESPOSTA_PADRAO
        texto, _ = garantir_citacao(texto, trechos)
        return RespostaModelo(provedor, modelo, versao, texto, round(time.perf_counter() - inicio, 2))
    except Exception as erro:  # noqa: BLE001
        return RespostaModelo(provedor, modelo, versao, "", round(time.perf_counter() - inicio, 2), str(erro))


def consultar_multiplos(
    pergunta: str,
    combinacoes: list[tuple[str, str, str]] | None = None,
    *,
    acesso_gestao: bool = False,
    cfg: ConfigRAG | None = None,
) -> tuple[list[RespostaModelo], list]:
    """(respostas de cada combinacao provedor/modelo/prompt, trechos recuperados)."""
    cfg = cfg or config_padrao()
    combinacoes = combinacoes or COMBINACOES_PADRAO
    if detectar_injection(pergunta):
        return [RespostaModelo(p, m, v, RESPOSTA_PADRAO, 0.0) for p, m, v in combinacoes], []
    trechos = recuperar(pergunta, cfg, acesso_gestao)
    if not trechos and cfg.recusa_sem_contexto:
        return [RespostaModelo(p, m, v, RESPOSTA_SEM_CONTEXTO, 0.0) for p, m, v in combinacoes], []
    contexto = montar_contexto(trechos)
    with ThreadPoolExecutor(max_workers=len(combinacoes)) as pool:
        futuros = [pool.submit(_responder, p, m, v, pergunta, contexto, trechos, cfg) for p, m, v in combinacoes]
        return [f.result() for f in futuros], trechos
