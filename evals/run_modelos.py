"""
Compara modelos de chat (mais de um provedor) na configuracao da iteracao 3.
O juiz RAGAS e sempre o mesmo, para a comparacao ser justa.

    python -m evals.run_modelos
    python -m evals.run_modelos --modelos groq:openai/gpt-oss-20b ollama:gemma4:cloud
"""

from __future__ import annotations

import argparse
import re

from evals.avaliar_rag import avaliar
from evals.consolidar import consolidar
from src.llm.provedores import MODELOS_DISPONIVEIS
from src.rag.config import ITERACAO_3


def slug(provedor: str, modelo: str) -> str:
    return "modelo_" + re.sub(r"[^a-z0-9]+", "_", f"{provedor}_{modelo}".lower()).strip("_")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--modelos", nargs="*", default=[f"{p}:{m}" for p, m in MODELOS_DISPONIVEIS])
    ap.add_argument("--sem-ragas", action="store_true")
    args = ap.parse_args()
    for item in args.modelos:
        provedor, modelo = item.split(":", 1)
        cfg = ITERACAO_3.com(provedor=provedor, modelo=modelo)
        avaliar(cfg, slug(provedor, modelo), descricao=f"iter3 com {provedor}:{modelo}", com_ragas=not args.sem_ragas)
    consolidar()


if __name__ == "__main__":
    main()
