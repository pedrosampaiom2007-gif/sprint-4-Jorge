"""
run_legado_rag.py — a coluna "Sprints 1/2 (versao original)" da tabela antes/depois.

Roda o chatbot das Sprints 1/2 (legado/chatbot_legado.py, busca por
palavra-chave em frases soltas, sem citacao) no MESMO eval set do RAG da
Sprint 4 e mede com as MESMAS metricas e o MESMO juiz RAGAS. Os patches do
comparativo da Sprint 3 continuam valendo (reasoning_format e stub de dados).

    python -m evals.run_legado_rag

Saida: evals/resultados/legado_sprints12.json
"""

from __future__ import annotations

import json
import time

from comparativo.run_comparativo import legado  # aplica os patches do legado ao importar
from evals.avaliar_rag import (
    EVAL_SET, JUIZ_PADRAO, PASTA_RESULTADOS, _media, _norm, _taxa, medir_ragas, parece_recusa, verificar_cota,
)
from src.contexto import contar_tokens


class _ClienteLangChain:
    """Imita client.chat.completions.create do SDK da Groq usando um modelo
    LangChain de qualquer provedor (src/llm/provedores.py)."""

    def __init__(self, provedor: str, modelo: str) -> None:
        self.provedor, self.modelo = provedor, modelo
        self.chat = self
        self.completions = self

    def create(self, model=None, messages=None, max_tokens=450, temperature=0.4, **_):
        from types import SimpleNamespace

        from src.llm.provedores import construir_llm

        llm = construir_llm(self.provedor, self.modelo, temperature=temperature, max_tokens=max_tokens)
        papeis = {"system": "system", "user": "human", "assistant": "ai"}
        texto = llm.invoke([(papeis[m["role"]], m["content"]) for m in messages]).content
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=str(texto)))])


def usar_modelo(provedor: str, modelo: str) -> None:
    """O legado chama o SDK da Groq direto. Para comparar com as iteracoes no MESMO
    modelo, troca o cliente por um adaptador com a mesma interface."""
    legado.MODELO = modelo
    legado.PROVEDOR_AVALIACAO = provedor
    if provedor != "groq":
        cliente = _ClienteLangChain(provedor, modelo)
        legado.obter_client = lambda: cliente


def main(pausa: float = 16.0, com_ragas: bool = True) -> dict:
    casos = json.loads(EVAL_SET.read_text(encoding="utf-8"))["casos"]
    linhas = []
    print(f"\n== LEGADO (Sprints 1/2) no eval set do RAG · {len(casos)} casos ==\n")
    for caso in casos:
        acesso = bool(caso.get("acesso_gestao", False))
        contexto = legado.buscar_contexto(caso["pergunta"], acesso_gestao=acesso)
        for tentativa in range(4):
            try:
                historico = []
                for anterior in caso.get("turnos_anteriores", []):
                    r = legado.responder(anterior, acesso_gestao=acesso, historico_anterior=historico)
                    historico += [{"role": "user", "content": anterior}, {"role": "assistant", "content": r}]
                inicio = time.perf_counter()
                resposta = legado.responder(caso["pergunta"], acesso_gestao=acesso, historico_anterior=historico)
                break
            except Exception as erro:  # noqa: BLE001  (erro de API nao vira resposta)
                verificar_cota(erro)
                if tentativa == 3:
                    raise RuntimeError(f"legado: caso {caso['id']} falhou apos 4 tentativas: {erro}") from erro
                time.sleep(15 * (tentativa + 1))
        latencia = time.perf_counter() - inicio

        chk = caso["checagens"]
        alvo = _norm(resposta)
        contem_ok = not chk.get("contem_algum") or any(_norm(x) in alvo for x in chk["contem_algum"])
        nao_contem_ok = all(_norm(x) not in alvo for x in chk.get("nao_contem", []))
        recusa_ok = parece_recusa(resposta) == bool(chk.get("deve_recusar", False))
        linhas.append({
            "id": caso["id"], "categoria": caso["categoria"], "pergunta": caso["pergunta"],
            "resposta": resposta, "contexto": contexto, "docs_esperados": caso.get("docs_esperados", []),
            "checagens_ok": contem_ok and nao_contem_ok and recusa_ok, "recusa_ok": recusa_ok,
            "trouxe_contexto": bool(contexto.strip()),
            "citou_fonte": ("Fonte" in resposta) if caso.get("docs_esperados") else None,
            "latencia_s": round(latencia, 2),
            "tokens_turno": contar_tokens(legado.SYSTEM_PROMPT) + contar_tokens(contexto)
            + contar_tokens(caso["pergunta"]) + contar_tokens(resposta),
            "faithfulness": None, "answer_relevancy": None,
        })
        print(f"  {'OK' if linhas[-1]['checagens_ok'] else 'XX'} [{caso['id']:>2}] {caso['categoria']:<20} "
              f"contexto={'sim' if contexto.strip() else 'nao'} {latencia:4.1f}s", flush=True)
        time.sleep(pausa)

    # Mesma regra da versao nova: RAGAS nos casos fundamentados que o modelo respondeu.
    # Sem contexto recuperado, o "contexto" medido e vazio — afirmacao sem base conta como infiel.
    medidos = [l for l in linhas if l["docs_esperados"] and not l["resposta"].startswith("[ERRO")]
    amostras = [{"user_input": l["pergunta"], "response": l["resposta"],
                 "retrieved_contexts": [l["contexto"] or "(nenhum contexto recuperado)"]} for l in medidos]
    if com_ragas and amostras:
        for linha, notas in zip(medidos, medir_ragas(amostras, JUIZ_PADRAO)):
            linha.update(notas)

    fundamentadas = [l for l in linhas if l["docs_esperados"]]
    a_recusar = [l for l in linhas if not l["docs_esperados"]]
    resumo = {
        "nome": "legado_sprints12",
        "descricao": "chatbot das Sprints 1/2: busca por palavra-chave em frases da planilha SP2, prompt v1, sem citacao",
        "config": {"versao_prompt": "legado (Sprints 1/2)", "estrategia_chunking": "frases soltas (sem chunking)",
                   "k": 5, "provedor": getattr(legado, "PROVEDOR_AVALIACAO", "groq"),
                   "modelo": legado.MODELO, "temperature": legado.TEMPERATURA},
        "juiz_ragas": f"{JUIZ_PADRAO[0]}:{JUIZ_PADRAO[1]}" if com_ragas else None,
        "n_casos": len(linhas),
        "n_ragas": sum(1 for l in linhas if l["faithfulness"] is not None),
        "faithfulness": _media(l["faithfulness"] for l in linhas),
        "answer_relevancy": _media(l["answer_relevancy"] for l in linhas),
        "recuperacao_hit": _taxa(l["trouxe_contexto"] for l in fundamentadas),
        "citacao_presente": _taxa(l["citou_fonte"] for l in fundamentadas),
        "respondeu_fundamentadas": _taxa(not parece_recusa(l["resposta"]) for l in fundamentadas),
        "recusa_correta": _taxa(l["recusa_ok"] for l in a_recusar),
        "checagens_ok": _taxa(l["checagens_ok"] for l in linhas),
        "latencia_media_s": _media(l["latencia_s"] for l in linhas),
        "tokens_turno_medio": _media(l["tokens_turno"] for l in linhas),
    }
    PASTA_RESULTADOS.mkdir(parents=True, exist_ok=True)
    (PASTA_RESULTADOS / "legado_sprints12.json").write_text(
        json.dumps({"resumo": resumo, "resultados": linhas}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(resumo, ensure_ascii=False, indent=2))
    return resumo


if __name__ == "__main__":
    import sys

    main(com_ragas="--sem-ragas" not in sys.argv)
