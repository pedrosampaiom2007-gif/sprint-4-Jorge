# Histórico de scores do RAG

Gerado por `python -m evals.consolidar` a partir de `evals/resultados/`.

## Iterações

- **Iteração 1:** chunk fixo 1000/150, prompt rag_v1, k=3, sem guardas em código.
- **Iteração 2:** chunk por seção 500/75 com cabeçalho, prompt rag_v2 (grounding + citação), limiar 0,45, recusa em código.
- **Iteração 3:** prompt rag_v3 com exemplos + reescrita da pergunta encadeada.

| Iteração | Faithfulness | Ganho | Answer relevancy | Ganho | Recuperação (hit@k) | Citação | Modelo citou [n] | Recusa correta |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Iteração 1 | 0,838 | — | 0,675 | — | 75% | 0% | 0% | 100% |
| Iteração 2 | pendente | — | pendente | — | pendente | pendente | pendente | pendente |
| Iteração 3 | pendente | — | pendente | — | pendente | pendente | pendente | pendente |

_Faithfulness e answer relevancy medidos com: rubrica de evals/fallback/rubrica_manual.md aplicada por LLM-juiz gemini:gemini-3.1-flash-lite. Modelo que respondeu: groq:openai/gpt-oss-20b._

## Antes e depois

| Critério | Sprints 1/2 (versão original) | Sprint 04 (RAG avaliado) |
|---|---|---|
| Recuperação | palavra-chave em 22 frases da planilha SP2 | busca vetorial (nomic-embed-text + ChromaDB) em 10 documentos, com filtro de acesso e limiar |
| Faithfulness | 0,350 | pendente |
| Faithfulness por iteração | versão única | it1 0,84 → it2 pendente → it3 pendente |
| Answer relevancy | 0,812 | pendente |
| Answer relevancy por iteração | versão única | it1 0,68 → it2 pendente → it3 pendente |
| Qualidade do contexto recuperado (documento certo entre os trechos) | 10% das perguntas trouxeram algum contexto (sem documento a conferir) | pendente |
| Presença de citação de fonte | 0% | pendente |
| Recusa correta (sem resposta na base, fora de escopo, dado restrito) | 100% | pendente |
| Checagens determinísticas OK | 46% | pendente |
| Latência média por turno | 0,59 s | pendente |
| Tokens por turno (média) | 1289 | pendente |

_Faithfulness e answer relevancy medidos com: rubrica de evals/fallback/rubrica_manual.md aplicada por LLM-juiz gemini:gemini-3.1-flash-lite. Modelo que respondeu: groq:openai/gpt-oss-20b._

## Modelos, parâmetros e juiz por etapa

| Etapa | Modelo que respondeu | temperature | top_p | max_tokens | k | Prompt | Juiz da rubrica |
|---|---|---:|---:|---:|---:|---|---|
| Sprints 1/2 | groq:openai/gpt-oss-20b | 0,4 | 1,0 | 450 | 5 | legado (Sprints 1/2) | gemini:gemini-3.1-flash-lite |
| Iteração 1 | groq:openai/gpt-oss-20b | 0,0 | 1,0 | 450 | 3 | rag_v1 | gemini:gemini-3.1-flash-lite |
| Iteração 2 | pendente | | | | | | |
| Iteração 3 | pendente | | | | | | |

## Modelos

| Modelo | temperature | top_p | max_tokens | k | Faithfulness | Answer relevancy | Recusa correta | Latência média | Tokens/turno |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| groq:openai/gpt-oss-20b | 0 | 1 | 450 | 4 | pendente | pendente | pendente | pendente | pendente |
| groq:openai/gpt-oss-120b | 0 | 1 | 450 | 4 | pendente | pendente | pendente | pendente | pendente |
| ollama:gemma4:cloud | 0 | 1 | 450 | 4 | pendente | pendente | pendente | pendente | pendente |
| gemini:gemini-3.1-flash-lite | 0 | 1 | 450 | 4 | pendente | pendente | pendente | pendente | pendente |

## Segurança

| Teste | Resultado |
|---|---|
| Injeção via documento | pendente |
| Bateria da Sprint 3 (24 casos, 12 ataques) | pendente |
