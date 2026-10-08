"""
cli.py — o chatbot no terminal.

    python -m app.cli --demo     3 turnos encadeados (memoria + reescrita da pergunta)
    python -m app.cli            conversa livre no terminal ('sair' encerra)

Precisa de GROQ_API_KEY e OLLAMA_API_KEY no .env. A orquestracao (guardrails +
RAG + chain + memoria) vive em src/assistente.py — aqui e so a casca de terminal.
A interface web esta em app/web.py.
"""

from __future__ import annotations

import argparse
import os
import sys

from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):  # stdout do Windows e cp1252 por padrao
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

load_dotenv()

_faltam = [v for v in ("GROQ_API_KEY", "OLLAMA_API_KEY") if not os.environ.get(v, "").strip()]
if _faltam:
    # Sem isto o erro vem como um traceback de 12 linhas la de dentro da
    # biblioteca, que nao ajuda ninguem a entender o que fazer.
    print(
        f"\nFalta no .env: {', '.join(_faltam)}.\n\n"
        "  1. Groq: https://console.groq.com/keys  |  Ollama: https://ollama.com -> Settings -> Keys\n"
        "  2. Copie o arquivo .env.example para .env\n"
        "  3. Cole as chaves nas linhas correspondentes\n\n"
        "Os testes offline nao precisam de chave nenhuma:\n"
        "  python -m unittest discover -s tests -v\n"
    )
    raise SystemExit(1)

from src.assistente import Assistente
from src.chain.memoria import limpar_sessao

# ferramenta interna da equipe -> acesso de gestao (ve faturamento/historico comercial).
_assistente = Assistente(acesso_gestao=True)


DEMO_TURNOS = [
    "Qual a tarifa base do ChargeGrid?",
    "E no horario de ponta?",                       # reescrita: "tarifa no horario de ponta"
    "Quanto fica uma recarga de 20 kWh nesse horario?",
]


def rodar_demo() -> None:
    sid = "demo"
    limpar_sessao(sid)
    print("=== DEMO — memoria em 3 turnos (mesmo session_id) ===\n")
    for i, pergunta in enumerate(DEMO_TURNOS, 1):
        print(f"[turno {i}] Voce: {pergunta}")
        print(f"[turno {i}] Bot : {_assistente.responder(pergunta, sid).resposta}\n")


def repl() -> None:
    sid = "terminal"
    print("ChargeGrid Intelligence — chatbot Sprint 4 (RAG). 'sair' encerra.\n")
    while True:
        try:
            pergunta = input("Voce: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAte mais!")
            break
        if not pergunta:
            continue
        if pergunta.lower() in ("sair", "exit", "quit"):
            print("Ate mais!")
            break
        print(f"Bot : {_assistente.responder(pergunta, sid).resposta}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chatbot ChargeGrid — Sprint 4")
    parser.add_argument("--demo", action="store_true", help="roda os 3 turnos de demonstracao de memoria")
    args = parser.parse_args()
    rodar_demo() if args.demo else repl()
