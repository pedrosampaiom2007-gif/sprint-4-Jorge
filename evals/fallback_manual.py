"""
fallback_manual.py — aplica a rubrica manual (evals/fallback/rubrica_manual.md)
nas respostas de uma iteracao.

    python -m evals.fallback_manual exportar   --resultado iter3
    python -m evals.fallback_manual consolidar --resultado iter3
    python -m evals.fallback_manual juiz-llm   --resultado iter3   # pre-preenche com um LLM

`exportar` gera uma planilha CSV com pergunta, trechos e resposta de cada caso
fundamentado; o avaliador preenche as duas notas. `consolidar` le a planilha e
grava as medias em "fallback_manual" dentro de evals/resultados/<iteracao>.json.
`juiz-llm` preenche a planilha usando a mesma rubrica num LLM — e um rascunho
para revisar a mao, nao substitui a revisao.
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_RAIZ = Path(__file__).resolve().parent.parent
PASTA_RESULTADOS = _RAIZ / "evals" / "resultados"
PASTA_FALLBACK = _RAIZ / "evals" / "fallback"
RUBRICA = PASTA_FALLBACK / "rubrica_manual.md"
COLUNAS = ["id", "pergunta", "trechos", "resposta", "faithfulness_manual", "answer_relevancy_manual", "observacao"]
NOTAS_VALIDAS = {0.0, 0.25, 0.5, 0.75, 1.0}


def _resultado(nome: str) -> tuple[Path, dict]:
    caminho = PASTA_RESULTADOS / f"{nome}.json"
    return caminho, json.loads(caminho.read_text(encoding="utf-8"))


def _planilha(nome: str) -> Path:
    return PASTA_FALLBACK / f"planilha_{nome}.csv"


def exportar(nome: str) -> Path:
    _, dados = _resultado(nome)
    destino = _planilha(nome)
    with destino.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS)
        w.writeheader()
        for linha in dados["resultados"]:
            if not linha.get("docs_esperados"):
                continue
            trechos = "\n---\n".join(f"[{i}] {t['citacao']}: {t['texto']}" for i, t in enumerate(linha["trechos"], 1))
            w.writerow({"id": linha["id"], "pergunta": linha["pergunta"], "trechos": trechos or "(nenhum)",
                        "resposta": linha["resposta"], "faithfulness_manual": "",
                        "answer_relevancy_manual": "", "observacao": ""})
    print(f"planilha: {destino}")
    return destino


def _nota(valor: str) -> float | None:
    if not str(valor).strip():
        return None
    nota = float(str(valor).replace(",", "."))
    if nota not in NOTAS_VALIDAS:
        raise ValueError(f"nota {valor} fora da rubrica (use 0, 0.25, 0.5, 0.75 ou 1)")
    return nota


def consolidar(nome: str) -> dict:
    caminho, dados = _resultado(nome)
    with _planilha(nome).open(encoding="utf-8") as f:
        linhas = list(csv.DictReader(f))
    faith = [n for n in (_nota(l["faithfulness_manual"]) for l in linhas) if n is not None]
    relev = [n for n in (_nota(l["answer_relevancy_manual"]) for l in linhas) if n is not None]
    resumo = {
        "faithfulness": round(statistics.mean(faith), 3) if faith else None,
        "answer_relevancy": round(statistics.mean(relev), 3) if relev else None,
        "n_avaliados": len(faith),
        "rubrica": str(RUBRICA.relative_to(_RAIZ)),
    }
    dados["resumo"]["fallback_manual"] = resumo
    caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(resumo, ensure_ascii=False, indent=2))
    return resumo


def juiz_llm(nome: str, provedor: str = "groq", modelo: str = "openai/gpt-oss-120b") -> Path:
    from pydantic import BaseModel, Field

    from src.llm.provedores import construir_llm

    class Notas(BaseModel):
        faithfulness: float = Field(description="0, 0.25, 0.5, 0.75 ou 1")
        answer_relevancy: float = Field(description="0, 0.25, 0.5, 0.75 ou 1")
        justificativa: str

    llm = construir_llm(provedor, modelo, temperature=0.0, max_tokens=800).with_structured_output(Notas)
    rubrica = RUBRICA.read_text(encoding="utf-8")
    destino = _planilha(nome)
    if not destino.exists():
        exportar(nome)
    with destino.open(encoding="utf-8") as f:
        linhas = list(csv.DictReader(f))
    for linha in linhas:
        pedido = (f"Aplique a rubrica abaixo e de as duas notas.\n\n{rubrica}\n\n"
                  f"PERGUNTA: {linha['pergunta']}\n\nTRECHOS:\n{linha['trechos']}\n\nRESPOSTA: {linha['resposta']}")
        notas = llm.invoke(pedido)
        arred = lambda v: min(NOTAS_VALIDAS, key=lambda n: abs(n - float(v)))  # noqa: E731
        linha["faithfulness_manual"] = arred(notas.faithfulness)
        linha["answer_relevancy_manual"] = arred(notas.answer_relevancy)
        linha["observacao"] = f"[rascunho LLM — revisar] {notas.justificativa}"
    with destino.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS)
        w.writeheader()
        w.writerows(linhas)
    print(f"planilha pre-preenchida: {destino}")
    return destino


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("acao", choices=["exportar", "consolidar", "juiz-llm"])
    ap.add_argument("--resultado", required=True, help="nome do resultado, ex.: iter3")
    args = ap.parse_args()
    {"exportar": exportar, "consolidar": consolidar, "juiz-llm": juiz_llm}[args.acao](args.resultado)


if __name__ == "__main__":
    main()
