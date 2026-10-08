"""
Prompts RAG versionados (prompts/rag/rag_vN.md) e montagem do <contexto>.

Cada trecho recuperado entra numerado, com documento e secao, para o modelo
citar [1], [2]... e para a interface mostrar de onde veio cada informacao.
"""

from __future__ import annotations

import re
from html import escape

from src.rag.loader import RAIZ

PASTA_PROMPTS = RAIZ / "prompts" / "rag"
VERSOES = ("rag_v1", "rag_v2", "rag_v3")

RESPOSTA_SEM_CONTEXTO = (
    "Não encontrei essa informação na base de conhecimento do ChargeGrid. "
    "Posso ajudar com recarga, tarifas, carregadores GoodWe ou uso em condomínio."
)

TEMPLATE_HUMANO = (
    "<contexto>\n{contexto}\n</contexto>\n\n"
    "<pergunta>\n{pergunta}\n</pergunta>"
)


def carregar_prompt_rag(versao: str) -> str:
    """Le prompts/rag/<versao>.md sem o comentario-cabecalho <!-- ... -->."""
    if versao not in VERSOES:
        raise ValueError(f"versao de prompt desconhecida: {versao} (use {', '.join(VERSOES)})")
    texto = (PASTA_PROMPTS / f"{versao}.md").read_text(encoding="utf-8")
    return re.sub(r"<!--.*?-->\s*", "", texto, count=1, flags=re.DOTALL).strip()


def montar_contexto(trechos: list, tempo_real: str = "") -> str:
    """Texto do <contexto>: trechos numerados e, se houver, os dados em tempo real."""
    blocos = []
    for i, t in enumerate(trechos, start=1):
        blocos.append(
            f'<documento id="{i}" fonte="{escape(t.titulo)}" secao="{escape(t.secao)}">\n'
            f"{t.texto}\n</documento>"
        )
    if tempo_real:
        blocos.append(f'<dados_tempo_real fonte="Sistema ChargeGrid">\n{tempo_real}\n</dados_tempo_real>')
    return "\n\n".join(blocos) if blocos else "(nenhum trecho relevante encontrado na base)"
