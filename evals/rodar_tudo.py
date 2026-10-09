"""
rodar_tudo.py — roda todas as avaliacoes da Sprint 4 num comando so e gera as
tabelas e o PDF.

    python -m evals.rodar_tudo
    python -m evals.rodar_tudo --modelos groq:openai/gpt-oss-20b groq:openai/gpt-oss-120b
    python -m evals.rodar_tudo --refazer          # apaga os resultados e comeca do zero
    python -m evals.rodar_tudo --so iter2         # so uma etapa (legado, iter1, iter2, iter3, modelos, seguranca)
    python -m evals.rodar_tudo --status           # o que ja terminou e o que falta
    python -m evals.rodar_tudo --juiz groq:openai/gpt-oss-20b   # outro juiz (cota diaria)
    python -m evals.rodar_tudo --geracao ollama:gemma4:cloud --juiz ollama:gemma4:cloud

--geracao troca o modelo que RESPONDE em todas as etapas (legado, iteracoes e
seguranca), para a comparacao antes/depois continuar no mesmo modelo.

A conta gratuita da Groq tem cota de tokens POR DIA por modelo. A ordem das etapas
poe primeiro o que entra na tabela antes/depois (legado e iteracoes); se a cota
acabar, rode de novo no dia seguinte e ele termina o resto.

As notas de faithfulness e answer_relevancy usam a rubrica de fallback
(evals/fallback/rubrica_manual.md) aplicada por um LLM-juiz, em vez do RAGAS:
menos dependencias para quebrar no meio (o RAGAS precisa do juiz E dos
embeddings ao mesmo tempo, em paralelo). Os comandos com RAGAS continuam
disponiveis (evals.run_iteracoes, evals.run_modelos).

Retoma de onde parou: etapa com resultado ja gravado e pulada, e a rubrica so
avalia os casos que ainda nao tem nota. Se cair no meio, e so rodar de novo.

Depois de CADA etapa que termina, as tabelas e o docs/relatorio_evolucao.pdf sao
regerados. Com COPIAR_PDF_PARA=<pasta> no ambiente (o notebook usa o Google Drive),
o PDF e copiado para la na hora — se a cota acabar no meio, o PDF que fica e o
mais atual.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import traceback
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_RAIZ = Path(__file__).resolve().parent.parent
PASTA = _RAIZ / "evals" / "resultados"
JUIZ_PADRAO = "groq:openai/gpt-oss-120b"
JUIZ = ("groq", "openai/gpt-oss-120b")


def _existe(nome: str) -> bool:
    return (PASTA / f"{nome}.json").exists()


def etapa(titulo: str, funcao, *args, **kwargs) -> bool:
    from evals.avaliar_rag import CotaEsgotada

    print(f"\n{'=' * 70}\n{titulo}\n{'=' * 70}", flush=True)
    try:
        funcao(*args, **kwargs)
        atualizar_relatorio()
        return True
    except CotaEsgotada as erro:
        atualizar_relatorio()
        # as proximas etapas usam a mesma conta: tentar seria so esperar e falhar
        print(f"\n[PAROU] {erro}")
        raise SystemExit(1)
    except SystemExit as saida:
        print(f"[parou] {saida}")
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        print(f"[falhou] {titulo} — rode o comando de novo para tentar so o que faltou")
    return False


def atualizar_relatorio() -> None:
    """Regera tabelas e PDF com o que ja terminou e copia o PDF, se pedido."""
    import os
    import shutil

    from evals.consolidar import consolidar

    try:
        consolidar(gerar_pdf=True, silencioso=True)
        destino = os.environ.get("COPIAR_PDF_PARA", "").strip()
        if destino:
            shutil.copy(_RAIZ / "docs" / "relatorio_evolucao.pdf", Path(destino) / "relatorio_evolucao.pdf")
        print(f"[relatorio atualizado{' e copiado para ' + destino if destino else ''}]", flush=True)
    except Exception as erro:  # noqa: BLE001  (relatorio nunca derruba a avaliacao)
        print(f"[aviso] relatorio nao atualizado: {erro}")


GERACAO: tuple[str, str] | None = None


def _modelo_do_resultado(nome: str) -> tuple[str, str] | None:
    import json

    config = json.loads((PASTA / f"{nome}.json").read_text(encoding="utf-8"))["resumo"].get("config", {})
    return (config.get("provedor"), config.get("modelo")) if config.get("modelo") else None


def separar_se_outro_modelo(nome: str) -> None:
    """Resultado feito com OUTRO modelo de geracao nao pode entrar na mesma tabela:
    vai para <nome>__<provedor>.bak e a etapa roda de novo com o modelo atual."""
    if not _existe(nome) or GERACAO is None or nome.startswith("modelo_"):
        return
    anterior = _modelo_do_resultado(nome)
    if anterior and anterior != GERACAO:
        destino = PASTA / f"{nome}__{anterior[0]}.bak"
        (PASTA / f"{nome}.json").rename(destino)
        print(f"{nome}.json era de {anterior[0]}:{anterior[1]} — guardado em {destino.name}; refazendo com "
              f"{GERACAO[0]}:{GERACAO[1]} para a tabela comparar o mesmo modelo")


def avaliar_com_rubrica(nome: str, gerar) -> None:
    from evals.fallback_manual import aplicar_rubrica_llm

    separar_se_outro_modelo(nome)
    if not _existe(nome):
        gerar()
    else:
        print(f"{nome}.json ja existe — so completando a rubrica")
    # o Gemini gratuito limita requisicoes por minuto: espaca mais as chamadas do juiz
    aplicar_rubrica_llm(nome, *JUIZ, pausa=5.0 if JUIZ[0] == "gemini" else 2.0)


ETAPAS = ["legado", "iter1", "iter2", "iter3", "modelos", "seguranca"]
NOMES_ETAPAS = {
    "legado": "Antes: chatbot das Sprints 1/2",
    "iter1": "Iteracao 1",
    "iter2": "Iteracao 2",
    "iter3": "Iteracao 3",
    "modelos": "Comparacao de modelos",
    "seguranca": "Testes de seguranca",
}


def _situacao_avaliacao(nome: str) -> str:
    import json

    if not _existe(nome):
        return "FALTA rodar"
    dados = json.loads((PASTA / f"{nome}.json").read_text(encoding="utf-8"))
    linhas = [l for l in dados.get("resultados", []) if l.get("docs_esperados")]
    com_nota = sum(1 for l in linhas if l.get("faithfulness_rubrica") is not None)
    config = dados.get("resumo", {}).get("config", {})
    modelo = f"{config.get('provedor')}:{config.get('modelo')}" if config.get("modelo") else "?"
    if com_nota < len(linhas):
        return f"FALTA completar a rubrica ({com_nota}/{len(linhas)} notas, {modelo}) — rode a celula de novo"
    return f"ok ({com_nota}/{len(linhas)} notas, {modelo})"


def mostrar_status() -> None:
    """Checklist das etapas: o que ja terminou e o que falta executar."""
    print("\nSITUACAO DAS ETAPAS")
    for etapa_ in ETAPAS:
        if etapa_ == "modelos":
            arquivos = sorted(PASTA.glob("modelo_*.json"))
            texto = ", ".join(f"{a.stem.replace('modelo_', '')}: {_situacao_avaliacao(a.stem)}" for a in arquivos) \
                or "FALTA rodar"
        elif etapa_ == "seguranca":
            feitos = [n for n in ("seguranca_documentos", "seguranca_sprint4") if _existe(n)]
            texto = "ok" if len(feitos) == 2 else f"FALTA rodar ({len(feitos)}/2 testes feitos)"
        else:
            texto = _situacao_avaliacao("legado_sprints12" if etapa_ == "legado" else etapa_)
        marca = "[ok]   " if texto.startswith("ok") else "[falta]"
        print(f"  {marca} {NOMES_ETAPAS[etapa_]:<32} {texto}")
    print()


def main() -> None:
    from evals.avaliar_rag import avaliar
    from evals.run_iteracoes import DESCRICOES
    from evals.run_modelos import slug
    from src.llm.provedores import MODELOS_DISPONIVEIS
    from src.rag.chunking import ESTRATEGIAS
    from src.rag.config import ITERACAO_3, ITERACOES
    from src.rag.vector_store import indexar

    ap = argparse.ArgumentParser(description="Todas as avaliacoes da Sprint 4")
    ap.add_argument("--modelos", nargs="*", default=[f"{p}:{m}" for p, m in MODELOS_DISPONIVEIS])
    ap.add_argument("--refazer", action="store_true", help="apaga os resultados anteriores")
    ap.add_argument("--juiz", default=JUIZ_PADRAO, help="provedor:modelo que aplica a rubrica")
    ap.add_argument("--geracao", default=None, help="provedor:modelo que responde (padrao: o da iteracao 3)")
    ap.add_argument("--so", nargs="*", choices=ETAPAS, help="roda so estas etapas")
    ap.add_argument("--status", action="store_true", help="mostra o que ja terminou e sai")
    args = ap.parse_args()
    if args.status:
        mostrar_status()
        return
    quer = (lambda e: e in args.so) if args.so else (lambda e: True)
    global JUIZ
    JUIZ = tuple(args.juiz.split(":", 1))

    import os

    geracao = tuple(args.geracao.split(":", 1)) if args.geracao else (ITERACAO_3.provedor, ITERACAO_3.modelo)
    global GERACAO
    GERACAO = geracao
    os.environ["RAG_PROVEDOR"], os.environ["RAG_MODELO"] = geracao
    print(f"modelo que responde: {geracao[0]}:{geracao[1]}  ·  juiz da rubrica: {JUIZ[0]}:{JUIZ[1]}")

    if args.refazer:
        for arquivo in PASTA.glob("*.json"):
            if arquivo.name != "sprint3_results.json":
                arquivo.unlink()

    status = {}
    if not args.so:
        status["indexacao"] = etapa("Indexacao da base", lambda: [print(indexar(e)) for e in ESTRATEGIAS])

    from evals import run_legado_rag

    run_legado_rag.usar_modelo(*geracao)
    if quer("legado"):
        status["legado"] = etapa("Antes: chatbot das Sprints 1/2", avaliar_com_rubrica, "legado_sprints12",
                                 lambda: run_legado_rag.main(com_ragas=False))

    for nome, cfg in ITERACOES.items():
        if not quer(nome):
            continue
        cfg = cfg.com(provedor=geracao[0], modelo=geracao[1])
        status[nome] = etapa(f"Sprint 4: {nome} — {DESCRICOES[nome]}", avaliar_com_rubrica, nome,
                             lambda cfg=cfg, nome=nome: avaliar(cfg, nome, com_ragas=False, descricao=DESCRICOES[nome]))

    for item in (args.modelos if quer("modelos") else []):
        provedor, modelo = item.split(":", 1)
        nome = slug(provedor, modelo)
        cfg = ITERACAO_3.com(provedor=provedor, modelo=modelo)
        if (provedor, modelo) == geracao and _existe("iter3") and not _existe(nome):
            # mesma configuracao da iteracao 3: reaproveita em vez de gastar a cota de novo
            import json

            dados = json.loads((PASTA / "iter3.json").read_text(encoding="utf-8"))
            dados["resumo"]["nome"] = nome
            dados["resumo"]["descricao"] = f"iter3 com {item} (mesma execucao da iteracao 3)"
            (PASTA / f"{nome}.json").write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
        status[nome] = etapa(f"Modelo {item}", avaliar_com_rubrica, nome,
                             lambda cfg=cfg, nome=nome, item=item: avaliar(cfg, nome, com_ragas=False,
                                                                            descricao=f"iter3 com {item}"))

    if quer("seguranca") and not _existe("seguranca_documentos"):
        from evals import seguranca_documentos

        status["seguranca_documentos"] = etapa("Injecao via documento", seguranca_documentos.main)
    if quer("seguranca") and not _existe("seguranca_sprint4"):
        status["seguranca_sprint4"] = etapa(
            "Bateria de seguranca da Sprint 3", subprocess.run,
            [sys.executable, "-m", "evals.run_evals", "--sem-juiz", "--modelo", geracao[1]], check=True, cwd=_RAIZ)

    if not args.so:
        etapa("Tabelas e PDF", lambda: None)

    falhas = [k for k, ok in status.items() if not ok]
    print("\n" + ("Etapa(s) concluida(s)." if not falhas else f"Etapas que falharam: {', '.join(falhas)} — rode de novo."))
    mostrar_status()


if __name__ == "__main__":
    main()
