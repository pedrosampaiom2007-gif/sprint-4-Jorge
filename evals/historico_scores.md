# Histórico de scores do RAG

Gerado por `python -m evals.consolidar` a partir de `evals/resultados/`.

## Iterações

- **Iteração 1:** chunk fixo 1000/150, prompt rag_v1, k=3, sem guardas em código.
- **Iteração 2:** chunk por seção 500/75 com cabeçalho, prompt rag_v2 (grounding + citação), limiar 0,45, recusa em código.
- **Iteração 3:** prompt rag_v3 com exemplos + reescrita da pergunta encadeada.

| Iteração | Faithfulness | Ganho | Answer relevancy | Ganho | Recuperação (hit@k) | Citação | Modelo citou [n] | Recusa correta |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Iteração 1 | pendente | — | pendente | — | pendente | pendente | pendente | pendente |
| Iteração 2 | pendente | — | pendente | — | pendente | pendente | pendente | pendente |
| Iteração 3 | pendente | — | pendente | — | pendente | pendente | pendente | pendente |

_Faithfulness e answer relevancy: pendente._

## Antes e depois

| Critério | Sprints 1/2 (versão original) | Sprint 04 (RAG avaliado) |
|---|---|---|
| Recuperação | palavra-chave em 22 frases da planilha SP2 | busca vetorial (nomic-embed-text + ChromaDB) em 10 documentos, com filtro de acesso e limiar |
| Faithfulness | pendente | pendente |
| Faithfulness por iteração | versão única | it1 pendente → it2 pendente → it3 pendente |
| Answer relevancy | pendente | pendente |
| Answer relevancy por iteração | versão única | it1 pendente → it2 pendente → it3 pendente |
| Qualidade do contexto recuperado (documento certo entre os trechos) | pendente | pendente |
| Presença de citação de fonte | pendente | pendente |
| Recusa correta (sem resposta na base, fora de escopo, dado restrito) | pendente | pendente |
| Checagens determinísticas OK | pendente | pendente |
| Latência média por turno | pendente | pendente |
| Tokens por turno (média) | pendente | pendente |

_Faithfulness e answer relevancy: pendente._

## Modelos

| Modelo | temperature | top_p | max_tokens | k | Faithfulness | Answer relevancy | Recusa correta | Latência média | Tokens/turno |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| groq:openai/gpt-oss-20b | 0 | 1 | 450 | 4 | pendente | pendente | pendente | pendente | pendente |
| groq:openai/gpt-oss-120b | 0 | 1 | 450 | 4 | pendente | pendente | pendente | pendente | pendente |
| ollama:gemma4:cloud | 0 | 1 | 450 | 4 | pendente | pendente | pendente | pendente | pendente |
| gemini:gemini-2.5-flash-lite | 0 | 1 | 450 | 4 | pendente | pendente | pendente | pendente | pendente |

## Segurança

| Teste | Resultado |
|---|---|
| Injeção via documento | pendente |
| Bateria da Sprint 3 (24 casos, 12 ataques) | pendente |
