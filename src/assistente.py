"""
assistente.py — orquestracao de um turno: guardrails -> RAG -> chain -> citacao -> memoria.

Ponto unico usado pela interface (app/), pela CLI e pelas avaliacoes (evals/),
para todos testarem exatamente o mesmo caminho.

    detectar_injection ─┐
                        ├─(barra sem gastar LLM)─> resposta padrao
    avaliar_escopo ─────┘
        │ ok
        v
    reescrever pergunta encadeada (se houver historico)
        v
    recuperar trechos (Chroma, filtro de acesso, limiar, blindagem)
        │ nada relevante e nada de tempo real -> recusa sem chamar o modelo
        v
    chain de conversa (com memoria por sessao)
        v
    guarda de saida -> citacao de fonte garantida
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field

warnings.filterwarnings("ignore", message=r".*RunnableWithMessageHistory.*")
try:
    from langchain_core._api import LangChainDeprecationWarning, LangChainPendingDeprecationWarning

    warnings.filterwarnings("ignore", category=LangChainDeprecationWarning)
    warnings.filterwarnings("ignore", category=LangChainPendingDeprecationWarning)
except Exception:  # noqa: BLE001
    pass

from dotenv import load_dotenv

load_dotenv()

from langchain_core.messages import AIMessage, HumanMessage  # noqa: E402

from src.chain.builder import construir_chain_conversa  # noqa: E402
from src.chain.memoria import com_memoria, historico_da_sessao  # noqa: E402
from src.guardrails.moderation import (  # noqa: E402
    RESPOSTA_PADRAO,
    detectar_injection,
    resposta_parece_vazamento,
)
from src.guardrails.scope_validator import avaliar_escopo  # noqa: E402
from src.integracao.dados_sistema import contexto_tempo_real  # noqa: E402
from src.llm.provedores import construir_llm  # noqa: E402
from src.rag.citacao import garantir_citacao  # noqa: E402
from src.rag.config import ConfigRAG, config_padrao  # noqa: E402
from src.rag.prompt_rag import RESPOSTA_SEM_CONTEXTO, montar_contexto  # noqa: E402
from src.rag.retriever import Trecho, recuperar, reescrever_pergunta  # noqa: E402


@dataclass
class Turno:
    resposta: str
    barrado_por: str | None  # None = passou pela chain; senao o rotulo do guardrail
    fontes: list[Trecho] = field(default_factory=list)      # trechos citados na resposta
    trechos: list[Trecho] = field(default_factory=list)     # tudo que foi entregue ao modelo
    contexto: str = ""
    pergunta_busca: str = ""
    resposta_modelo: str = ""                               # texto do modelo, sem a linha de fontes


class Assistente:
    """Guarda a chain (com memoria) montada uma vez para uma ConfigRAG."""

    def __init__(
        self,
        cfg: ConfigRAG | None = None,
        *,
        acesso_gestao: bool = False,
        max_tokens_historico: int = 800,
        versao_prompt: str | None = None,
    ) -> None:
        cfg = cfg or config_padrao()
        if versao_prompt:
            cfg = cfg.com(versao_prompt=versao_prompt)
        self.cfg = cfg
        self.versao_prompt = cfg.versao_prompt
        self._acesso_padrao = acesso_gestao
        self._max_tokens_historico = max_tokens_historico
        llm_kwargs = dict(provedor=cfg.provedor, model=cfg.modelo, temperature=cfg.temperature,
                          top_p=cfg.top_p, max_tokens=cfg.max_tokens)
        chain = construir_chain_conversa(versao_prompt=cfg.versao_prompt, **llm_kwargs)
        self._chain = com_memoria(chain, max_tokens=max_tokens_historico)
        self._llm_reescrita = None

    def _reescrever(self, pergunta: str, session_id: str) -> str:
        if not self.cfg.reescrever_pergunta:
            return pergunta
        historico = historico_da_sessao(session_id, max_tokens=self._max_tokens_historico).messages
        if not historico:
            return pergunta
        if self._llm_reescrita is None:
            self._llm_reescrita = construir_llm(self.cfg.provedor, self.cfg.modelo, temperature=0.0,
                                                top_p=1.0, max_tokens=120)
        return reescrever_pergunta(pergunta, historico, self._llm_reescrita)

    def _registrar(self, session_id: str, pergunta: str, resposta: str) -> None:
        historico_da_sessao(session_id, max_tokens=self._max_tokens_historico).add_messages(
            [HumanMessage(content=pergunta), AIMessage(content=resposta)]
        )

    def responder(
        self, pergunta: str, session_id: str = "default", *, acesso_gestao: bool | None = None
    ) -> Turno:
        # --- guardrails de codigo: so os de ALTA precisao barram sem LLM ---
        rotulo = detectar_injection(pergunta)
        if rotulo:
            return Turno(f"{RESPOSTA_PADRAO}   [guardrail: {rotulo}]", f"injection:{rotulo}")

        escopo = avaliar_escopo(pergunta)
        if escopo.categoria in ("dominio_restrito", "comparacao_produto"):
            sufixo = f"/{escopo.subdominio}" if escopo.subdominio else ""
            return Turno(
                f"{escopo.resposta_padrao}   [guardrail: {escopo.categoria}{sufixo}]",
                f"{escopo.categoria}{sufixo}",
            )

        acesso = self._acesso_padrao if acesso_gestao is None else acesso_gestao

        # --- RAG: pergunta completa -> trechos -> <contexto> ---
        pergunta_busca = self._reescrever(pergunta, session_id)
        trechos = recuperar(pergunta_busca, self.cfg, acesso)
        tempo_real = contexto_tempo_real(pergunta_busca, acesso)

        # grounding em codigo: sem trecho relevante e sem dado de tempo real,
        # nao ha do que responder — recusa sem chamar o modelo.
        if not trechos and not tempo_real and self.cfg.recusa_sem_contexto:
            self._registrar(session_id, pergunta, RESPOSTA_SEM_CONTEXTO)
            return Turno(RESPOSTA_SEM_CONTEXTO, "sem-contexto", pergunta_busca=pergunta_busca)

        contexto = montar_contexto(trechos, tempo_real)
        texto = self._chain.invoke(
            {"pergunta": pergunta, "contexto": contexto},
            config={"configurable": {"session_id": session_id}},
        )

        # guarda de SAIDA: vazamento de prompt nao vai para a tela nem fica na memoria
        if resposta_parece_vazamento(texto):
            hist = historico_da_sessao(session_id, max_tokens=self._max_tokens_historico)
            if hist.messages:
                del hist.messages[-2:]
            return Turno(f"{RESPOSTA_PADRAO}   [guardrail: vazamento-na-saida]", "vazamento-na-saida",
                         trechos=trechos, contexto=contexto, pergunta_busca=pergunta_busca)

        if self.cfg.citacao_garantida:
            final, citados = garantir_citacao(texto, trechos)
        else:
            from src.rag.citacao import referencias_citadas

            final = texto
            citados = [trechos[n - 1] for n in referencias_citadas(texto, len(trechos))]
        return Turno(final, None, fontes=citados, trechos=trechos, contexto=contexto,
                     pergunta_busca=pergunta_busca, resposta_modelo=texto)
