"""
web.py — interface web do chatbot (Gradio).

    python -m app.web            # http://localhost:7860
    python -m app.web --share    # link publico temporario

Abas:
    Chat               conversa com o RAG; cada resposta mostra as fontes citadas
    Comparar modelos   a mesma pergunta em mais de um provedor/modelo/prompt
    Base               documentos indexados e botao de reindexar
    Avaliacao          scores por iteracao (evals/historico_scores.md)
"""

from __future__ import annotations

import argparse
import os
import sys
import traceback
import uuid
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

load_dotenv()

from src.assistente import Assistente  # noqa: E402
from src.chain.memoria import limpar_sessao  # noqa: E402
from src.llm.multi_provider import COMBINACOES_PADRAO, consultar_multiplos  # noqa: E402
from src.llm.provedores import MODELOS_DISPONIVEIS, chaves_faltando, rotulo  # noqa: E402
from src.rag.config import config_padrao  # noqa: E402
from src.rag.loader import carregar_base, resumo_base  # noqa: E402
from src.rag.prompt_rag import VERSOES  # noqa: E402

_RAIZ = Path(__file__).resolve().parent.parent
TITULO = "ChargeGrid Intelligence — assistente de recarga"
PERFIS = {"Motorista (app/totem)": False, "Gestão (ferramenta interna)": True}
MODELOS = [rotulo(p, m) for p, m in MODELOS_DISPONIVEIS]
EXEMPLOS = [
    "Quanto custa o kWh no horário de ponta?",
    "Qual o grau de proteção IP do carregador GoodWe HCA?",
    "Quais normas técnicas a instalação de carregadores em condomínio deve seguir?",
    "Em quanto tempo o morador deve liberar a vaga depois da recarga?",
    "Qual ponto de carga teve mais receita no histórico?",
    "Qual o preço do carregador GoodWe HCA de 22 kW?",
]


@lru_cache(maxsize=8)
def _assistente(modelo: str, versao: str) -> Assistente:
    provedor, nome = modelo.split(":", 1)
    return Assistente(config_padrao().com(provedor=provedor, modelo=nome, versao_prompt=versao))


def painel_fontes(turno) -> str:
    """Markdown com cada trecho entregue ao modelo; os citados vem marcados."""
    if turno.barrado_por and not turno.trechos:
        return f"**Sem consulta à base** — barrado por `{turno.barrado_por}`."
    if not turno.trechos:
        return "_Nenhum trecho recuperado._"
    citados = {t.chunk_id for t in turno.fontes}
    linhas = []
    if turno.pergunta_busca:
        linhas.append(f"**Pergunta usada na busca:** {turno.pergunta_busca}\n")
    for i, t in enumerate(turno.trechos, 1):
        url = t.metadados.get("url") or ""
        nome = f"[{t.titulo}]({url})" if url else t.titulo
        marca = "✅ citado" if t.chunk_id in citados else "consultado"
        aviso = " · ⚠️ instrução removida" if t.suspeito else ""
        corpo = t.texto.split("\n", 1)[-1][:500]
        linhas.append(
            f"**[{i}] {nome} › {t.secao}** — {marca} · relevância {t.score:.2f}{aviso}\n\n> {corpo}\n"
        )
    return "\n".join(linhas)


def responder(mensagem, historico, sessao, perfil, modelo, versao):
    mensagem = (mensagem or "").strip()
    historico = list(historico or [])
    if not mensagem:
        return historico, "", gr_noop(), sessao
    faltam = chaves_faltando({modelo.split(":", 1)[0], "ollama"})
    if faltam:
        aviso = f"⚠️ Falta no .env: {', '.join(faltam)}"
        return historico + [_msg("user", mensagem), _msg("assistant", aviso)], "", aviso, sessao
    try:
        turno = _assistente(modelo, versao).responder(mensagem, session_id=sessao, acesso_gestao=PERFIS[perfil])
        resposta, fontes = turno.resposta, painel_fontes(turno)
    except Exception as erro:  # noqa: BLE001
        traceback.print_exc()
        resposta, fontes = f"⚠️ Não consegui responder agora: `{erro}`", ""
    return historico + [_msg("user", mensagem), _msg("assistant", resposta)], "", fontes, sessao


def nova_conversa(sessao):
    limpar_sessao(sessao)
    novo = str(uuid.uuid4())
    return [], "_Faça uma pergunta._", novo


def comparar(pergunta, perfil, selecionados):
    pergunta = (pergunta or "").strip()
    if not pergunta:
        return "_Escreva uma pergunta._"
    combinacoes = [c for c in COMBINACOES_PADRAO if _rotulo_combo(c) in (selecionados or [])]
    if not combinacoes:
        return "_Marque pelo menos uma combinação._"
    faltam = chaves_faltando({c[0] for c in combinacoes} | {"ollama"})
    if faltam:
        return f"⚠️ Falta no .env: {', '.join(faltam)}"
    respostas, trechos = consultar_multiplos(pergunta, combinacoes, acesso_gestao=PERFIS[perfil])
    blocos = [f"**Trechos recuperados (os mesmos para todos):** {len(trechos)}\n"]
    for r in respostas:
        corpo = r.resposta if not r.erro else f"⚠️ erro: `{r.erro}`"
        blocos.append(f"### {r.rotulo}  ·  {r.latencia_s:.1f} s\n\n{corpo}\n")
    return "\n".join(blocos)


def _rotulo_combo(c) -> str:
    return f"{rotulo(c[0], c[1])} · {c[2]}"


def tabela_base() -> str:
    linhas = ["| Documento | Tipo | Acesso | Páginas/seções | Caracteres |", "|---|---|---|---:|---:|"]
    for r in resumo_base(carregar_base()):
        linhas.append(f"| {r['titulo']} | {r['tipo']} | {r['acesso']} | {r['unidades']} | {r['caracteres']} |")
    return "\n".join(linhas)


def reindexar() -> str:
    from src.rag.chunking import ESTRATEGIAS
    from src.rag.vector_store import indexar

    try:
        return "\n".join(f"- `{r['colecao']}`: {r['chunks']} chunks ({r['indexados_agora']} indexados agora)"
                         for r in (indexar(e) for e in ESTRATEGIAS))
    except Exception as erro:  # noqa: BLE001
        traceback.print_exc()
        return f"⚠️ Falha ao indexar: `{erro}`"


def scores() -> str:
    caminho = _RAIZ / "evals" / "historico_scores.md"
    return caminho.read_text(encoding="utf-8") if caminho.exists() else "_Rode `python -m evals.run_iteracoes`._"


def _msg(papel: str, texto: str) -> dict:
    return {"role": papel, "content": texto}


def gr_noop():
    import gradio as gr

    return gr.update()


def construir_interface():
    import gradio as gr

    major = int(str(gr.__version__).split(".")[0])
    chatbot_kwargs = {} if major >= 6 else {"type": "messages"}
    cfg = config_padrao()

    with gr.Blocks(title=TITULO) as demo:
        gr.Markdown(f"# ⚡ {TITULO}\nEV Challenge GoodWe / FIAP · Sprint 4 — RAG com ChromaDB, "
                    "nomic-embed-text e citação de fonte.")
        sessao = gr.State(str(uuid.uuid4()))

        with gr.Tab("💬 Chat"):
            with gr.Row():
                with gr.Column(scale=3):
                    chat = gr.Chatbot(height=480, label="Assistente", **chatbot_kwargs)
                    entrada = gr.Textbox(placeholder="Pergunte sobre recarga, tarifas, GoodWe HCA, condomínio...",
                                         label="Pergunta", lines=2)
                    with gr.Row():
                        enviar = gr.Button("Enviar", variant="primary")
                        limpar = gr.Button("Nova conversa")
                    gr.Examples(EXEMPLOS, inputs=entrada, label="Exemplos")
                with gr.Column(scale=2):
                    perfil = gr.Radio(list(PERFIS), value=list(PERFIS)[0], label="Perfil de acesso")
                    modelo = gr.Dropdown(MODELOS, value=rotulo(cfg.provedor, cfg.modelo), label="Modelo")
                    versao = gr.Dropdown(list(VERSOES), value=cfg.versao_prompt, label="Versão do prompt RAG")
                    gr.Markdown("### Fontes desta resposta")
                    fontes = gr.Markdown("_Faça uma pergunta._")

        with gr.Tab("⚖️ Comparar modelos"):
            gr.Markdown("A mesma pergunta e os mesmos trechos, respondidos por mais de um provedor, "
                        "modelo e versão de prompt.")
            pergunta_cmp = gr.Textbox(label="Pergunta", lines=2)
            perfil_cmp = gr.Radio(list(PERFIS), value=list(PERFIS)[0], label="Perfil de acesso")
            combos = gr.CheckboxGroup([_rotulo_combo(c) for c in COMBINACOES_PADRAO],
                                      value=[_rotulo_combo(c) for c in COMBINACOES_PADRAO], label="Combinações")
            botao_cmp = gr.Button("Comparar", variant="primary")
            saida_cmp = gr.Markdown()

        with gr.Tab("📚 Base de conhecimento"):
            gr.Markdown(tabela_base())
            botao_idx = gr.Button("Reindexar")
            saida_idx = gr.Markdown()

        with gr.Tab("📊 Avaliação"):
            painel_scores = gr.Markdown(scores())
            gr.Button("Atualizar").click(scores, None, painel_scores)

        entradas = [entrada, chat, sessao, perfil, modelo, versao]
        saidas = [chat, entrada, fontes, sessao]
        enviar.click(responder, entradas, saidas)
        entrada.submit(responder, entradas, saidas)
        limpar.click(nova_conversa, sessao, [chat, fontes, sessao])
        botao_cmp.click(comparar, [pergunta_cmp, perfil_cmp, combos], saida_cmp)
        botao_idx.click(reindexar, None, saida_idx)
    return demo


def main() -> None:
    ap = argparse.ArgumentParser(description=TITULO)
    ap.add_argument("--share", action="store_true")
    ap.add_argument("--porta", type=int, default=int(os.environ.get("PORTA", 7860)))
    args = ap.parse_args()
    construir_interface().launch(server_name="127.0.0.1", server_port=args.porta, share=args.share)


if __name__ == "__main__":
    main()
