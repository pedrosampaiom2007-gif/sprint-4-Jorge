"""
avaliar_rag.py — roda o eval set do RAG (evals/eval_set_rag.json) numa
configuracao do pipeline e mede:

  RAGAS
    faithfulness       fracao das afirmacoes da resposta sustentadas pelos trechos
    answer_relevancy   o quanto a resposta trata do que foi perguntado
  Sem LLM-juiz
    recuperacao_ok     algum documento esperado veio entre os trechos (hit@k)
    citou_fonte        resposta fundamentada saiu com fonte (linha "Fontes:" ou [n])
    modelo_citou       o proprio modelo citou [n], sem contar a linha que o codigo acrescenta
    recusa_ok          recusou quando devia e respondeu quando devia
    checagens_ok       contem_algum / nao_contem / recusa
    latencia, tokens por turno

Uso:
  python -m evals.avaliar_rag --iteracao iter1
  python -m evals.avaliar_rag --iteracao iter3 --provedor ollama --modelo gemma4:cloud --nome modelo_gemma4
  python -m evals.avaliar_rag --iteracao iter3 --sem-ragas      # so as metricas sem juiz

Saida: evals/resultados/<nome>.json  (nome padrao = a iteracao)
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import time
import unicodedata
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from src.assistente import Assistente, Turno  # noqa: E402
from src.chain.builder import carregar_prompt  # noqa: E402
from src.chain.memoria import limpar_sessao  # noqa: E402
from src.contexto import contar_tokens  # noqa: E402
from src.llm.provedores import chaves_faltando, construir_llm  # noqa: E402
from src.rag.citacao import e_recusa, referencias_citadas  # noqa: E402
from src.rag.config import ITERACOES, ConfigRAG  # noqa: E402
from src.rag.vector_store import indexar  # noqa: E402

_RAIZ = Path(__file__).resolve().parent.parent
EVAL_SET = _RAIZ / "evals" / "eval_set_rag.json"
PASTA_RESULTADOS = _RAIZ / "evals" / "resultados"

JUIZ_PADRAO = ("groq", "openai/gpt-oss-120b")

_MARCAS_RECUSA = (
    "nao encontrei", "so consigo ajudar", "nao posso", "restrita a gestao", "nao tenho",
    "nao esta disponivel", "nao disponivel", "nao consta", "nao ha informacao", "[guardrail:",
)


def _norm(t: str) -> str:
    t = unicodedata.normalize("NFKD", str(t).lower())
    return "".join(c for c in t if not unicodedata.combining(c))


def parece_recusa(resposta: str) -> bool:
    alvo = _norm(resposta)
    return e_recusa(resposta) or any(m in alvo for m in _MARCAS_RECUSA)


def checar(caso: dict, turno: Turno) -> dict:
    chk = caso.get("checagens", {})
    alvo = _norm(turno.resposta)
    contem_ok = not chk.get("contem_algum") or any(_norm(x) in alvo for x in chk["contem_algum"])
    nao_contem_ok = all(_norm(x) not in alvo for x in chk.get("nao_contem", []))
    recusou = parece_recusa(turno.resposta)
    recusa_ok = recusou == bool(chk.get("deve_recusar", False))
    esperados = set(caso.get("docs_esperados", []))
    recuperados = {t.doc_id for t in turno.trechos}
    fundamentada = bool(esperados)
    return {
        "contem_ok": contem_ok,
        "nao_contem_ok": nao_contem_ok,
        "recusa_ok": recusa_ok,
        "checagens_ok": contem_ok and nao_contem_ok and recusa_ok,
        "recuperacao_ok": bool(esperados & recuperados) if fundamentada else None,
        "citou_fonte": ("Fontes" in turno.resposta or bool(referencias_citadas(turno.resposta, len(turno.trechos))))
        if fundamentada and not recusou else None,
        "modelo_citou": bool(referencias_citadas(turno.resposta_modelo or turno.resposta, len(turno.trechos)))
        if fundamentada and not recusou else None,
    }


def rodar_caso(assistente: Assistente, caso: dict, prefixo: str) -> tuple[Turno, float]:
    sid = f"{prefixo}-{caso['id']}"
    limpar_sessao(sid)
    acesso = bool(caso.get("acesso_gestao", False))
    for anterior in caso.get("turnos_anteriores", []):
        assistente.responder(anterior, session_id=sid, acesso_gestao=acesso)
    inicio = time.perf_counter()
    for tentativa in range(4):
        try:
            turno = assistente.responder(caso["pergunta"], session_id=sid, acesso_gestao=acesso)
            break
        except Exception as erro:  # noqa: BLE001  (rate limit da conta gratuita)
            if tentativa == 3:
                turno = Turno(f"[ERRO apos retries: {erro}]", "erro")
                break
            time.sleep(15 * (tentativa + 1))
    return turno, time.perf_counter() - inicio


def medir_ragas(amostras: list[dict], juiz: tuple[str, str]) -> list[dict]:
    """faithfulness e answer_relevancy por amostra (NaN quando o RAGAS nao consegue medir)."""
    from ragas import EvaluationDataset, evaluate
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from ragas.llms import LangchainLLMWrapper
    from ragas.metrics import Faithfulness, ResponseRelevancy
    from ragas.run_config import RunConfig

    from src.rag.embeddings import criar_embeddings

    llm = LangchainLLMWrapper(construir_llm(juiz[0], juiz[1], temperature=0.0, top_p=1.0, max_tokens=2000))
    emb = LangchainEmbeddingsWrapper(criar_embeddings())
    resultado = evaluate(
        dataset=EvaluationDataset.from_list(amostras),
        metrics=[Faithfulness(), ResponseRelevancy()],
        llm=llm,
        embeddings=emb,
        run_config=RunConfig(timeout=300, max_retries=8, max_wait=90, max_workers=2),
        show_progress=True,
    )
    df = resultado.to_pandas()
    return [
        {"faithfulness": _num(df.iloc[i].get("faithfulness")),
         "answer_relevancy": _num(df.iloc[i].get("answer_relevancy"))}
        for i in range(len(df))
    ]


def _num(v) -> float | None:
    try:
        v = float(v)
        return None if math.isnan(v) else round(v, 3)
    except (TypeError, ValueError):
        return None


def _media(valores) -> float | None:
    valores = [v for v in valores if v is not None]
    return round(statistics.mean(valores), 3) if valores else None


def _taxa(valores) -> float | None:
    valores = [v for v in valores if v is not None]
    return round(sum(bool(v) for v in valores) / len(valores), 3) if valores else None


def avaliar(cfg: ConfigRAG, nome: str, *, com_ragas: bool = True, juiz: tuple[str, str] = JUIZ_PADRAO,
            pausa: float = 4.0, descricao: str = "") -> dict:
    """Roda o eval set inteiro com a configuracao e grava evals/resultados/<nome>.json."""
    casos = json.loads(EVAL_SET.read_text(encoding="utf-8"))["casos"]
    faltam = chaves_faltando({cfg.provedor, juiz[0]} if com_ragas else {cfg.provedor})
    if faltam:
        raise SystemExit(f"Faltam variaveis no .env: {', '.join(faltam)}")

    print(f"\n== {nome}: {cfg.versao_prompt} · {cfg.estrategia_chunking} · k={cfg.k} · "
          f"{cfg.provedor}:{cfg.modelo} · {len(casos)} casos ==")
    print(f"   indice: {indexar(cfg.estrategia_chunking)}\n")

    assistente = Assistente(cfg)
    system_tokens = contar_tokens(carregar_prompt(cfg.versao_prompt))
    linhas = []
    for caso in casos:
        turno, latencia = rodar_caso(assistente, caso, nome)
        chk = checar(caso, turno)
        tokens = system_tokens + contar_tokens(turno.contexto) + contar_tokens(caso["pergunta"]) \
            + contar_tokens(turno.resposta) if turno.barrado_por is None else 0
        linhas.append({
            "id": caso["id"], "categoria": caso["categoria"], "pergunta": caso["pergunta"],
            "pergunta_busca": turno.pergunta_busca, "resposta": turno.resposta,
            "resposta_modelo": turno.resposta_modelo, "barrado_por": turno.barrado_por,
            "trechos": [t.como_dict() for t in turno.trechos],
            "docs_esperados": caso.get("docs_esperados", []),
            "resposta_referencia": caso.get("resposta_referencia", ""),
            **chk, "latencia_s": round(latencia, 2), "tokens_turno": tokens,
            "faithfulness": None, "answer_relevancy": None,
        })
        marca = "OK" if chk["checagens_ok"] else "XX"
        print(f"  {marca} [{caso['id']:>2}] {caso['categoria']:<20} rec={chk['recuperacao_ok']} "
              f"cit={chk['citou_fonte']} {latencia:4.1f}s", flush=True)
        time.sleep(pausa)

    # RAGAS so onde existe resposta fundamentada a medir: caso com documento
    # esperado, que passou pelo modelo e veio com trecho.
    medidos = [l for l in linhas if l["docs_esperados"] and l["barrado_por"] is None and l["trechos"]]
    if com_ragas and medidos:
        amostras = [{
            "user_input": l["pergunta_busca"] or l["pergunta"],
            "response": l["resposta_modelo"] or l["resposta"],
            "retrieved_contexts": [t["texto"] for t in l["trechos"]],
        } for l in medidos]
        for linha, notas in zip(medidos, medir_ragas(amostras, juiz)):
            linha.update(notas)

    fundamentadas = [l for l in linhas if l["docs_esperados"]]
    a_recusar = [l for l in linhas if not l["docs_esperados"]]
    resumo = {
        "nome": nome,
        "descricao": descricao,
        "config": cfg.como_dict(),
        "juiz_ragas": f"{juiz[0]}:{juiz[1]}" if com_ragas else None,
        "n_casos": len(linhas),
        "n_ragas": sum(1 for l in linhas if l["faithfulness"] is not None),
        "faithfulness": _media(l["faithfulness"] for l in linhas),
        "answer_relevancy": _media(l["answer_relevancy"] for l in linhas),
        "recuperacao_hit": _taxa(l["recuperacao_ok"] for l in fundamentadas),
        "citacao_presente": _taxa(l["citou_fonte"] for l in fundamentadas),
        "modelo_citou": _taxa(l["modelo_citou"] for l in fundamentadas),
        "respondeu_fundamentadas": _taxa(not parece_recusa(l["resposta"]) for l in fundamentadas),
        "recusa_correta": _taxa(l["recusa_ok"] for l in a_recusar),
        "checagens_ok": _taxa(l["checagens_ok"] for l in linhas),
        "latencia_media_s": _media(l["latencia_s"] for l in linhas),
        "tokens_turno_medio": _media(l["tokens_turno"] for l in linhas if l["tokens_turno"]),
    }
    PASTA_RESULTADOS.mkdir(parents=True, exist_ok=True)
    saida = PASTA_RESULTADOS / f"{nome}.json"
    saida.write_text(json.dumps({"resumo": resumo, "resultados": linhas}, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    print("\n== RESUMO ==")
    for chave, valor in resumo.items():
        if chave not in ("config", "descricao"):
            print(f"  {chave:<24} {valor}")
    print(f"\n  arquivo: {saida}\n")
    return resumo


def main() -> None:
    ap = argparse.ArgumentParser(description="Avaliacao do RAG (RAGAS + metricas sem juiz)")
    ap.add_argument("--iteracao", default="iter3", choices=sorted(ITERACOES))
    ap.add_argument("--provedor", default=None)
    ap.add_argument("--modelo", default=None)
    ap.add_argument("--nome", default=None, help="nome do arquivo de saida (padrao: a iteracao)")
    ap.add_argument("--sem-ragas", action="store_true")
    ap.add_argument("--juiz", default=":".join(JUIZ_PADRAO), help="provedor:modelo do juiz RAGAS")
    ap.add_argument("--pausa", type=float, default=4.0, help="segundos entre casos (TPM da conta gratuita)")
    args = ap.parse_args()

    cfg = ITERACOES[args.iteracao]
    if args.provedor:
        cfg = cfg.com(provedor=args.provedor)
    if args.modelo:
        cfg = cfg.com(modelo=args.modelo)
    provedor_juiz, modelo_juiz = args.juiz.split(":", 1)
    avaliar(cfg, args.nome or args.iteracao, com_ragas=not args.sem_ragas,
            juiz=(provedor_juiz, modelo_juiz), pausa=args.pausa)


if __name__ == "__main__":
    main()
