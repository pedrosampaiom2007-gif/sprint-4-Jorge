# Chatbot ChargeGrid Intelligence — Sprint 4

**EV Challenge — GoodWe / FIAP · Prompt and Artificial Intelligence · 2026.2**
Turma 1CCPG

Assistente de recarga e gestão de eletropostos. Na Sprint 4 o chatbot passa a responder
com base num **RAG** — documentos do domínio vetorizados com `nomic-embed-text` num
**ChromaDB persistente** —, cita a fonte em toda resposta, recusa o que não está na base,
é medido com **RAGAS** e ganhou uma **interface web**.

- Relatório de evolução (PDF): [`docs/relatorio_evolucao.pdf`](docs/relatorio_evolucao.pdf)
- RAG: [`docs/relatorio_rag.md`](docs/relatorio_rag.md) · Modelos e parâmetros: [`docs/relatorio_modelos.md`](docs/relatorio_modelos.md)
- Scores por iteração: [`evals/historico_scores.md`](evals/historico_scores.md) · Versões do prompt: [`prompts/rag/CHANGELOG.md`](prompts/rag/CHANGELOG.md)

---

## Integrantes

| Nome | RM |
|------|----|
| Luan de Araujo Carneiro | 573691 |
| Pedro Sampaio Mochnacs Arruda | 573522 |
| Raul Sampaio Mochnacs Arruda | 573523 |
| Pedro Ribeiro Lopes | 570083 |
| Kevin Rodrigues de Melo | 571777 |
| Pedro Vianna | 570747 |

---

## Rodando o projeto

Precisa de Python 3.11 a 3.13.

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux / Mac

pip install -r requirements.txt
copy .env.example .env          # Windows  (Linux/Mac: cp .env.example .env)
```

No `.env`, preencha as duas chaves — nenhuma chave fica no repositório:

```
GROQ_API_KEY=...      # https://console.groq.com/keys
OLLAMA_API_KEY=...    # https://ollama.com -> Settings -> Keys
```

Depois:

```bash
python -m src.rag.vector_store   # indexa a base no ChromaDB (data/chroma/)
python -m app.web                # interface web em http://localhost:7860
python -m app.cli                # ou no terminal
```

Se a Ollama Cloud não servir o `nomic-embed-text` na sua conta, instale o Ollama
(<https://ollama.com/download>), rode `ollama pull nomic-embed-text` e coloque
`OLLAMA_EMBED_BASE_URL=http://localhost:11434` no `.env`.

### Avaliação

```bash
python -m evals.calibrar_limiar         # confere o limiar de relevância (só embeddings)
python -m evals.run_legado_rag          # coluna "antes": chatbot das Sprints 1/2
python -m evals.run_iteracoes           # iterações 1, 2 e 3 com RAGAS
python -m evals.run_modelos             # gpt-oss-20b x gpt-oss-120b x gemma4:cloud
python -m evals.seguranca_documentos    # prompt injection escondido em documento
python -m evals.run_evals               # bateria de segurança da Sprint 3 (24 casos)
python -m evals.consolidar              # atualiza tabelas dos relatórios e o PDF
```

> A conta gratuita da Groq limita 8 mil tokens por minuto. As avaliações fazem pausa
> entre os casos e repetem a chamada quando batem no limite; a rodada completa leva
> algumas dezenas de minutos.

Sem RAGAS (biblioteca falhando, limite de requisições): rubrica manual equivalente em
[`evals/fallback/rubrica_manual.md`](evals/fallback/rubrica_manual.md), aplicada com
`python -m evals.fallback_manual`.

### Testes

```bash
python -m unittest discover -s tests -v    # rodam offline, sem chave
```

---

## Como o chatbot funciona

```
pergunta
   |
   v
guardrails            barram ataque e assunto perigoso antes de gastar chamada
   |
   v
reescrita             "e no horário de ponta?" vira pergunta completa (se houver histórico)
   |
   v
busca no ChromaDB     nomic-embed-text, top-4, limiar de relevância,
   |                  filtro de acesso (relatório comercial só para a gestão)
   v
blindagem             tira frase com instrução escondida dentro dos trechos
   |                  nada relevante -> "Não encontrei essa informação na base"
   v
prompt RAG (v3)       trechos numerados com documento e seção + histórico + pergunta
   |
   v
modelo                groq:openai/gpt-oss-20b, temperatura 0
   |
   v
guarda de saída       vazamento de prompt vira recusa
   |
   v
citação               linha "Fontes: [1] documento › seção" garantida em código
```

---

## Onde está cada coisa

```
data/knowledge_base/       base de conhecimento (PDFs + documentos do projeto) e fontes.json
src/
  rag/                     loader, chunking, embeddings, vector_store, retriever,
                           prompt_rag, blindagem, citacao, config (iterações)
  llm/                     provedores (Groq, Ollama) e chamada multi-provider
  assistente.py            junta guardrails + RAG + chain + memória + citação
  chain/                   chain LCEL e memória por tokens (Sprint 3)
  guardrails/              prompt injection e escopo (Sprint 3)
  schemas/                 ConsultaRecarga — resposta estruturada
  integracao/              dados de tempo real (estações, faturamento)
app/                       interface web (Gradio) e terminal
prompts/rag/               prompt RAG versionado (rag_v1..v3) + CHANGELOG
evals/                     eval sets, RAGAS, fallback manual, resultados por iteração
docs/                      relatório de evolução (PDF), relatorio_rag.md, relatorio_modelos.md
comparativo/, legado/      versão das Sprints 1/2 e o comparativo da Sprint 3
tests/                     testes offline
```

---

## Como adicionar documentos à base

1. Coloque o arquivo em `data/knowledge_base/`.
   - **PDF:** acrescente uma entrada em `data/knowledge_base/fontes.json` com `titulo`,
     `tipo`, `acesso` (`publico` ou `gestao`), `url` de origem, `autoria` e `ano`.
   - **Markdown:** comece o arquivo com o cabeçalho YAML (`titulo`, `tipo`, `acesso`...)
     e separe as seções com `## Título` — cada seção aparece na citação.
2. Rode `python -m src.rag.vector_store` (ou **Reindexar** na interface).
3. Rode `python -m evals.calibrar_limiar` e a avaliação para conferir que nada piorou.

---

## Segurança

- **Grounding:** responde só com os trechos recuperados; sem trecho relevante, recusa
  sem chamar o modelo.
- **Citação:** toda resposta fundamentada sai com documento e seção.
- **Fora do contexto:** recusa com frase fixa; jurídico, financeiro e instalação elétrica
  são encaminhados a um profissional.
- **Prompt injection na pergunta:** as 5 camadas da Sprint 3.
- **Prompt injection via documento:** a blindagem troca a frase dirigida ao assistente
  por um aviso antes de o trecho chegar ao modelo, e o prompt manda tratar documento
  como dado. Teste: `python -m evals.seguranca_documentos`.
- **Dados de gestão:** o relatório comercial tem `acesso: gestao` e é filtrado na busca.
- **Especificação de produto:** o prompt proíbe informar o que não está escrito num trecho.

---

## Limitações conhecidas

- A apresentação do Secovi de 2026 é quase toda imagem; sem OCR, contribui pouco.
- O manual GoodWe está em inglês; o modelo explica em português, e a busca depende do
  `nomic-embed-text` aproximar pergunta em português de texto em inglês.
- Os dados de tempo real (estações livres, faturamento) continuam fixos, para a
  avaliação dar sempre o mesmo resultado.
