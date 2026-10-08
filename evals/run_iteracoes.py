"""
Roda as tres iteracoes do RAG em sequencia e consolida os relatorios.

    python -m evals.run_iteracoes
"""

from __future__ import annotations

from evals.avaliar_rag import avaliar
from evals.consolidar import consolidar
from src.rag.config import ITERACOES

DESCRICOES = {
    "iter1": "linha de base: chunk fixo de 1000, prompt rag_v1, k=3, sem guardas em codigo",
    "iter2": "chunk por secao (500) com cabecalho, prompt rag_v2 com grounding e citacao, limiar 0,45 e recusa em codigo",
    "iter3": "prompt rag_v3 com exemplos + reescrita da pergunta encadeada",
}


def main() -> None:
    for nome, cfg in ITERACOES.items():
        avaliar(cfg, nome, descricao=DESCRICOES[nome])
    consolidar()


if __name__ == "__main__":
    main()
