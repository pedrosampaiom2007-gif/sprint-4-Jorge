"""
Citacao de fonte em toda resposta.

O prompt pede para o modelo citar [n], mas prompt nao e garantia. Aqui a
resposta sai sempre com a linha "Fontes:" listando documento e secao:
- se o modelo citou [n], lista so os trechos citados;
- se nao citou, lista os trechos que foram entregues a ele ("Fontes consultadas");
- recusa e resposta sem trecho nenhum nao recebem fonte.
"""

from __future__ import annotations

import re
import unicodedata

from src.rag.prompt_rag import RESPOSTA_SEM_CONTEXTO

_REF = re.compile(r"\[(\d{1,2})\]")
_MARCAS_RECUSA = (
    "nao encontrei essa informacao", "nao posso fazer isso", "so consigo ajudar",
    "restrita a gestao", "[guardrail:",
)


def _norm(t: str) -> str:
    t = unicodedata.normalize("NFKD", t.lower())
    return "".join(c for c in t if not unicodedata.combining(c))


def e_recusa(resposta: str) -> bool:
    alvo = _norm(resposta)
    return _norm(RESPOSTA_SEM_CONTEXTO[:40]) in alvo or any(m in alvo for m in _MARCAS_RECUSA)


def referencias_citadas(resposta: str, total: int) -> list[int]:
    """Numeros [n] citados que existem de fato entre os trechos, sem repetir."""
    vistos: list[int] = []
    for m in _REF.finditer(resposta):
        n = int(m.group(1))
        if 1 <= n <= total and n not in vistos:
            vistos.append(n)
    return vistos


def garantir_citacao(resposta: str, trechos: list) -> tuple[str, list]:
    """(texto final com a linha de fontes, trechos efetivamente citados)."""
    texto = resposta.strip()
    if not trechos or e_recusa(texto):
        return texto, []
    citados = referencias_citadas(texto, len(trechos))
    if citados:
        usados = [(n, trechos[n - 1]) for n in citados]
        rotulo = "Fontes"
    else:
        usados = list(enumerate(trechos, start=1))
        rotulo = "Fontes consultadas"
    linha = "; ".join(f"[{n}] {t.citacao()}" for n, t in usados)
    return f"{texto}\n\n{rotulo}: {linha}", [t for _, t in usados]
