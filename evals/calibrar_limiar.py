"""
calibrar_limiar.py — escolhe o limiar de relevancia com dados, sem LLM.

Para cada pergunta do eval set, pega a relevancia do MELHOR trecho recuperado.
Pergunta com resposta na base deveria ter relevancia alta; pergunta sem resposta
(fora da base, fora de escopo), baixa. O limiar bom separa os dois grupos.

    python -m evals.calibrar_limiar
    python -m evals.calibrar_limiar --estrategia fixo_1000

So usa embeddings (nomic-embed-text). Saida: evals/resultados/calibracao_limiar.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from src.rag.config import ITERACAO_3  # noqa: E402
from src.rag.retriever import recuperar  # noqa: E402
from src.rag.vector_store import indexar  # noqa: E402

_RAIZ = Path(__file__).resolve().parent.parent


def main() -> dict:
    ap = argparse.ArgumentParser()
    ap.add_argument("--estrategia", default=ITERACAO_3.estrategia_chunking)
    args = ap.parse_args()

    indexar(args.estrategia)
    cfg = ITERACAO_3.com(estrategia_chunking=args.estrategia, limiar_relevancia=0.0, k=4, blindagem_documentos=False)
    casos = json.loads((_RAIZ / "evals" / "eval_set_rag.json").read_text(encoding="utf-8"))["casos"]
    linhas = []
    for c in casos:
        if c.get("turnos_anteriores"):
            continue  # a pergunta crua ("e no horario de ponta?") depende da reescrita
        trechos = recuperar(c["pergunta"], cfg, bool(c.get("acesso_gestao")))
        melhor = trechos[0].score if trechos else 0.0
        linhas.append({"id": c["id"], "pergunta": c["pergunta"], "tem_resposta": bool(c["docs_esperados"]),
                       "melhor_score": melhor, "melhor_doc": trechos[0].doc_id if trechos else None})

    com = sorted(l["melhor_score"] for l in linhas if l["tem_resposta"])
    sem = sorted(l["melhor_score"] for l in linhas if not l["tem_resposta"])
    candidatos = [round(x / 100, 2) for x in range(20, 81)]

    def acertos(limiar: float) -> int:
        return sum(s >= limiar for s in com) + sum(s < limiar for s in sem)

    melhor = max(candidatos, key=lambda t: (acertos(t), -abs(t - 0.45)))
    resultado = {
        "estrategia": args.estrategia,
        "score_com_resposta": {"min": com[0] if com else None, "max": com[-1] if com else None},
        "score_sem_resposta": {"min": sem[0] if sem else None, "max": sem[-1] if sem else None},
        "limiar_sugerido": melhor,
        "acertos_no_limiar": f"{acertos(melhor)}/{len(com) + len(sem)}",
        "casos": linhas,
    }
    saida = _RAIZ / "evals" / "resultados" / "calibracao_limiar.json"
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    for l in linhas:
        print(f"  {'COM' if l['tem_resposta'] else 'SEM'} {l['melhor_score']:.3f}  {l['pergunta'][:70]}")
    print(f"\nlimiar sugerido: {melhor}  (acerta {resultado['acertos_no_limiar']})")
    print("Se for diferente de 0,45, ajuste RAG_LIMIAR no .env ou limiar_relevancia em src/rag/config.py.")
    return resultado


if __name__ == "__main__":
    main()
