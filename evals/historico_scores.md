# Histórico de scores do RAG

Gerado por `python -m evals.consolidar` a partir de `evals/resultados/`.

## Iterações

- **Iteração 1:** chunk fixo 1000/150, prompt rag_v1, k=3, sem guardas em código.
- **Iteração 2:** chunk por seção 500/75 com cabeçalho, prompt rag_v2 (grounding + citação), limiar 0,45, recusa em código.
- **Iteração 3:** prompt rag_v3 com exemplos + reescrita da pergunta encadeada.

| Iteração | Faithfulness | Ganho | Answer relevancy | Ganho | Recuperação (hit@k) | Citação | Modelo citou [n] | Recusa correta |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Iteração 1 | 0,838 | — | 0,675 | — | 75% | 0% | 0% | 100% |
| Iteração 2 | 0,988 | +0,150 | 0,725 | +0,050 | 85% | 100% | 100% | 100% |
| Iteração 3 | 0,988 | +0,000 | 0,750 | +0,025 | 85% | 100% | 93% | 75% |

_Faithfulness e answer relevancy medidos com: rubrica de evals/fallback/rubrica_manual.md aplicada por LLM-juiz gemini:gemini-3.1-flash-lite. Modelo que respondeu: groq:openai/gpt-oss-20b._

## Antes e depois

| Critério | Sprints 1/2 (versão original) | Sprint 04 (RAG avaliado) |
|---|---|---|
| Recuperação | palavra-chave em 22 frases da planilha SP2 | busca vetorial (nomic-embed-text + ChromaDB) em 10 documentos, com filtro de acesso e limiar |
| Faithfulness | 0,350 | 0,988 |
| Faithfulness por iteração | versão única | it1 0,84 → it2 0,99 → it3 0,99 |
| Answer relevancy | 0,812 | 0,750 |
| Answer relevancy por iteração | versão única | it1 0,68 → it2 0,72 → it3 0,75 |
| Qualidade do contexto recuperado (documento certo entre os trechos) | 10% das perguntas trouxeram algum contexto (sem documento a conferir) | 85% |
| Presença de citação de fonte | 0% | 100% |
| Recusa correta (sem resposta na base, fora de escopo, dado restrito) | 100% | 75% |
| Checagens determinísticas OK | 46% | 67% |
| Latência média por turno | 0,59 s | 9,98 s |
| Tokens por turno (média) | 1289 | 2475 |

_Faithfulness e answer relevancy medidos com: rubrica de evals/fallback/rubrica_manual.md aplicada por LLM-juiz gemini:gemini-3.1-flash-lite. Modelo que respondeu: groq:openai/gpt-oss-20b._

## Modelos, parâmetros e juiz por etapa

| Etapa | temperature | top_p | max_tokens | k | Prompt |
|---|---:|---:|---:|---:|---|
| Sprints 1/2 | 0,4 | 1,0 | 450 | 5 | legado (Sprints 1/2) |
| Iteração 1 | 0,0 | 1,0 | 450 | 3 | rag_v1 |
| Iteração 2 | 0,0 | 1,0 | 450 | 4 | rag_v2 |
| Iteração 3 | 0,0 | 1,0 | 450 | 4 | rag_v3 |

_Modelo que respondeu em todas as etapas: groq:openai/gpt-oss-20b. Juiz da rubrica: gemini:gemini-3.1-flash-lite._

_Embeddings registrados nas execuções: nomic-embed-text via Ollama em http://127.0.0.1:11434._

## Modelos

| Modelo | temperature | top_p | max_tokens | k | Faithfulness | Answer relevancy | Recusa correta | Latência média | Tokens/turno |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| gemini:gemini-3.1-flash-lite | 0 | 1 | 450 | 4 | 1,000 | 0,738 | 100% | 3,04 s | 2493 |
| groq:openai/gpt-oss-120b | 0 | 1 | 450 | 4 | 1,000 | 0,700 | 100% | 9,30 s | 2463 |
| groq:openai/gpt-oss-20b | 0 | 1 | 450 | 4 | 0,988 | 0,750 | 75% | 9,98 s | 2475 |
| ollama:gemma4:cloud | 0 | 1 | 450 | 4 | 0,988 | 0,738 | 100% | 0,79 s | 2470 |

## Segurança

| Teste | Resultado |
|---|---|
| Injeção via documento — com blindagem | resistiu em 3/3 |
| Injeção via documento — sem blindagem (só o prompt) | resistiu em 2/3 |
| Bateria da Sprint 3 (24 casos, 12 ataques) | checagens 71%, ataques recusados 100% |
