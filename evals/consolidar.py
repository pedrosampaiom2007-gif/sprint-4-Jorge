"""
consolidar.py — junta os resultados de evals/resultados/ em tabelas e atualiza
os relatorios.

    python -m evals.consolidar

Gera evals/historico_scores.md e reescreve, nos arquivos abaixo, o trecho entre
os marcadores <!-- AUTO:nome --> e <!-- /AUTO:nome -->:

    docs/relatorio_evolucao.md   docs/relatorio_rag.md   docs/relatorio_modelos.md
    prompts/rag/CHANGELOG.md

Depois regera docs/relatorio_evolucao.pdf. Resultado que ainda nao existe aparece
como "pendente", entao da para rodar a qualquer momento.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

_RAIZ = Path(__file__).resolve().parent.parent
PASTA = _RAIZ / "evals" / "resultados"
PENDENTE = "pendente"

ARQUIVOS_COM_TABELAS = [
    _RAIZ / "docs" / "relatorio_evolucao.md",
    _RAIZ / "docs" / "relatorio_rag.md",
    _RAIZ / "docs" / "relatorio_modelos.md",
    _RAIZ / "prompts" / "rag" / "CHANGELOG.md",
]


def carregar(nome: str) -> dict | None:
    caminho = PASTA / f"{nome}.json"
    if not caminho.exists():
        return None
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    return dados.get("resumo", dados)


def num(v, casas: int = 3) -> str:
    return PENDENTE if v is None else f"{v:.{casas}f}".replace(".", ",")


def seg(v) -> str:
    return PENDENTE if v is None else f"{num(v, 2)} s"


def pct(v) -> str:
    return PENDENTE if v is None else f"{v * 100:.0f}%"


def delta(atual, anterior) -> str:
    if atual is None or anterior is None:
        return "—"
    d = atual - anterior
    return ("+" if d >= 0 else "") + f"{d:.3f}".replace(".", ",")


def _g(r: dict | None, chave: str):
    return None if r is None else r.get(chave)


def _metrica(r: dict | None, chave: str):
    """Rubrica de fallback quando ela foi aplicada; senao RAGAS. A rubrica vem
    primeiro para todas as colunas usarem a MESMA medida — um RAGAS parcial
    (interrompido por limite de cota) misturado com rubrica nao e comparavel."""
    if r and r.get("fallback_manual") and r["fallback_manual"].get(chave) is not None:
        return r["fallback_manual"][chave]
    return _g(r, chave)


def fonte_metricas() -> str:
    """De onde vieram faithfulness e answer_relevancy nas tabelas."""
    fontes = set()
    for nome in ["legado_sprints12", "iter1", "iter2", "iter3"] + [p.stem for p in PASTA.glob("modelo_*.json")]:
        r = carregar(nome)
        if not r:
            continue
        if r.get("fallback_manual") and r["fallback_manual"].get("faithfulness") is not None:
            fontes.add(r["fallback_manual"].get("metodo") or "rubrica de fallback (evals/fallback/rubrica_manual.md)")
        elif r.get("faithfulness") is not None and r.get("juiz_ragas"):
            fontes.add(f"RAGAS (juiz {r['juiz_ragas']})")
    if not fontes:
        return "_Faithfulness e answer relevancy: pendente._"
    modelos = sorted({f"{r['config']['provedor']}:{r['config']['modelo']}"
                      for r in (carregar(n) for n in ("legado_sprints12", "iter1", "iter2", "iter3")) if r and r.get("config")})
    linha_modelo = f" Modelo que respondeu: {', '.join(modelos)}." if modelos else ""
    return "_Faithfulness e answer relevancy medidos com: " + "; ".join(sorted(fontes)) + "." + linha_modelo + "_"


ITERACOES = [
    ("iter1", "Iteração 1", "chunk fixo 1000/150, prompt rag_v1, k=3, sem guardas em código"),
    ("iter2", "Iteração 2", "chunk por seção 500/75 com cabeçalho, prompt rag_v2 (grounding + citação), limiar 0,45, recusa em código"),
    ("iter3", "Iteração 3", "prompt rag_v3 com exemplos + reescrita da pergunta encadeada"),
]


def tabela_iteracoes() -> str:
    linhas = [f"- **{rotulo}:** {mudanca}." for _, rotulo, mudanca in ITERACOES]
    linhas += [
        "",
        "| Iteração | Faithfulness | Ganho | Answer relevancy | Ganho | Recuperação (hit@k) | Citação | Modelo citou [n] | Recusa correta |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    anterior = None
    for nome, rotulo, _ in ITERACOES:
        r = carregar(nome)
        f, a = _metrica(r, "faithfulness"), _metrica(r, "answer_relevancy")
        linhas.append(
            f"| {rotulo} | {num(f)} | {delta(f, _metrica(anterior, 'faithfulness'))} | "
            f"{num(a)} | {delta(a, _metrica(anterior, 'answer_relevancy'))} | {pct(_g(r, 'recuperacao_hit'))} | "
            f"{pct(_g(r, 'citacao_presente'))} | {pct(_g(r, 'modelo_citou'))} | {pct(_g(r, 'recusa_correta'))} |"
        )
        anterior = r
    return "\n".join(linhas) + "\n\n" + fonte_metricas()


def _contexto_legado(r: dict | None) -> str:
    v = _g(r, "recuperacao_hit")
    return PENDENTE if v is None else f"{pct(v)} das perguntas trouxeram algum contexto (sem documento a conferir)"


def tabela_antes_depois() -> str:
    antes = carregar("legado_sprints12")
    its = [carregar(n) for n, _, _ in ITERACOES]
    depois = its[-1]
    scores_iter = " → ".join(f"it{i} {num(_metrica(r, 'faithfulness'), 2)}" for i, r in enumerate(its, 1))
    relev_iter = " → ".join(f"it{i} {num(_metrica(r, 'answer_relevancy'), 2)}" for i, r in enumerate(its, 1))
    linhas = [
        "| Critério | Sprints 1/2 (versão original) | Sprint 04 (RAG avaliado) |",
        "|---|---|---|",
        "| Recuperação | palavra-chave em 22 frases da planilha SP2 | busca vetorial (nomic-embed-text + ChromaDB) em 10 documentos, com filtro de acesso e limiar |",
        f"| Faithfulness | {num(_metrica(antes, 'faithfulness'))} | {num(_metrica(depois, 'faithfulness'))} |",
        f"| Faithfulness por iteração | versão única | {scores_iter} |",
        f"| Answer relevancy | {num(_metrica(antes, 'answer_relevancy'))} | {num(_metrica(depois, 'answer_relevancy'))} |",
        f"| Answer relevancy por iteração | versão única | {relev_iter} |",
        f"| Qualidade do contexto recuperado (documento certo entre os trechos) | {_contexto_legado(antes)} | {pct(_g(depois, 'recuperacao_hit'))} |",
        f"| Presença de citação de fonte | {pct(_g(antes, 'citacao_presente'))} | {pct(_g(depois, 'citacao_presente'))} |",
        f"| Recusa correta (sem resposta na base, fora de escopo, dado restrito) | {pct(_g(antes, 'recusa_correta'))} | {pct(_g(depois, 'recusa_correta'))} |",
        f"| Checagens determinísticas OK | {pct(_g(antes, 'checagens_ok'))} | {pct(_g(depois, 'checagens_ok'))} |",
        f"| Latência média por turno | {seg(_g(antes, 'latencia_media_s'))} | {seg(_g(depois, 'latencia_media_s'))} |",
        f"| Tokens por turno (média) | {num(_g(antes, 'tokens_turno_medio'), 0)} | {num(_g(depois, 'tokens_turno_medio'), 0)} |",
    ]
    return "\n".join(linhas) + "\n\n" + fonte_metricas()


def _modelos() -> list[dict]:
    return [json.loads(p.read_text(encoding="utf-8"))["resumo"] for p in sorted(PASTA.glob("modelo_*.json"))]


def tabela_modelos() -> str:
    linhas = [
        "| Modelo | temperature | top_p | max_tokens | k | Faithfulness | Answer relevancy | Recusa correta | Latência média | Tokens/turno |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    modelos = _modelos()
    if not modelos:
        from src.llm.provedores import MODELOS_DISPONIVEIS

        for provedor, modelo in MODELOS_DISPONIVEIS:
            linhas.append(f"| {provedor}:{modelo} | 0 | 1 | 450 | 4 | {PENDENTE} | {PENDENTE} | {PENDENTE} | {PENDENTE} | {PENDENTE} |")
        return "\n".join(linhas)
    for r in modelos:
        c = r["config"]
        linhas.append(
            f"| {c['provedor']}:{c['modelo']} | {c['temperature']:g} | {c['top_p']:g} | {c['max_tokens']} | {c['k']} | "
            f"{num(_metrica(r, 'faithfulness'))} | {num(_metrica(r, 'answer_relevancy'))} | {pct(r.get('recusa_correta'))} | "
            f"{seg(r.get('latencia_media_s'))} | {num(r.get('tokens_turno_medio'), 0)} |"
        )
    return "\n".join(linhas)


def tabela_prompts() -> str:
    from src.contexto import contar_tokens
    from src.rag.prompt_rag import carregar_prompt_rag

    linhas = [
        "| Versão | Tokens do prompt | Usada na | Faithfulness | Answer relevancy | Ganho de faithfulness vs versão anterior |",
        "|---|---:|---|---:|---:|---:|",
    ]
    anterior = None
    for (nome, rotulo, _), versao in zip(ITERACOES, ("rag_v1", "rag_v2", "rag_v3")):
        r = carregar(nome)
        f = _metrica(r, "faithfulness")
        linhas.append(
            f"| {versao} | {contar_tokens(carregar_prompt_rag(versao))} | {rotulo} | {num(f)} | "
            f"{num(_metrica(r, 'answer_relevancy'))} | {delta(f, _metrica(anterior, 'faithfulness'))} |"
        )
        anterior = r
    return "\n".join(linhas)


def tabela_seguranca() -> str:
    doc = carregar("seguranca_documentos")
    seg = carregar("seguranca_sprint4")
    linhas = ["| Teste | Resultado |", "|---|---|"]
    if doc:
        for chave, rotulo in (("com_blindagem", "Injeção via documento — com blindagem"),
                              ("sem_blindagem", "Injeção via documento — sem blindagem (só o prompt)")):
            r = doc.get(chave, {})
            linhas.append(f"| {rotulo} | resistiu em {r.get('resistiu', '?')}/{r.get('total', '?')} |")
    else:
        linhas.append(f"| Injeção via documento | {PENDENTE} |")
    if seg:
        linhas.append(f"| Bateria da Sprint 3 (24 casos, 12 ataques) | checagens {pct(seg.get('taxa_checagens_ok'))}, "
                      f"ataques recusados {pct(seg.get('recusa_jailbreak'))} |")
    else:
        linhas.append(f"| Bateria da Sprint 3 (24 casos, 12 ataques) | {PENDENTE} |")
    return "\n".join(linhas)


TABELAS = {
    "iteracoes": tabela_iteracoes,
    "antes_depois": tabela_antes_depois,
    "modelos": tabela_modelos,
    "prompts": tabela_prompts,
    "seguranca": tabela_seguranca,
}


def substituir_marcadores(texto: str, tabelas: dict[str, str]) -> str:
    for nome, conteudo in tabelas.items():
        padrao = re.compile(rf"(<!-- AUTO:{nome} -->).*?(<!-- /AUTO:{nome} -->)", re.DOTALL)
        texto = padrao.sub(lambda m: f"{m.group(1)}\n{conteudo}\n{m.group(2)}", texto)
    return texto


def consolidar(gerar_pdf: bool = True) -> dict[str, str]:
    tabelas = {nome: f() for nome, f in TABELAS.items()}
    historico = (
        "# Histórico de scores do RAG\n\n"
        "Gerado por `python -m evals.consolidar` a partir de `evals/resultados/`.\n\n"
        "## Iterações\n\n" + tabelas["iteracoes"] + "\n\n"
        "## Antes e depois\n\n" + tabelas["antes_depois"] + "\n\n"
        "## Modelos\n\n" + tabelas["modelos"] + "\n\n"
        "## Segurança\n\n" + tabelas["seguranca"] + "\n"
    )
    (_RAIZ / "evals" / "historico_scores.md").write_text(historico, encoding="utf-8")
    for caminho in ARQUIVOS_COM_TABELAS:
        if caminho.exists():
            caminho.write_text(substituir_marcadores(caminho.read_text(encoding="utf-8"), tabelas), encoding="utf-8")
    if gerar_pdf:
        try:
            from docs.gerar_pdf import main as gerar

            gerar()
        except Exception as erro:  # noqa: BLE001
            print(f"[aviso] PDF nao gerado: {erro}")
    print(historico)
    return tabelas


if __name__ == "__main__":
    consolidar()
