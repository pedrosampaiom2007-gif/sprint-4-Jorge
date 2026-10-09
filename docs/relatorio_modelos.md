# Modelos e parâmetros — Sprint 4

## Provedores

| Provedor | Modelo | Papel |
|---|---|---|
| Groq | `openai/gpt-oss-20b` | modelo de produção do chatbot |
| Groq | `openai/gpt-oss-120b` | comparado no chat |
| Ollama Cloud | `gemma4:cloud` | comparado no chat; segundo provedor da chamada multi-provider |
| Google AI Studio | `gemini-3.1-flash-lite` (o primeiro de `GEMINI_CANDIDATOS` que a chave aceita) | comparado no chat; **juiz da rubrica** nas avaliações |
| Ollama local (no Colab, `127.0.0.1:11434`) | `nomic-embed-text` | embeddings (indexação e busca); a Ollama Cloud devolvia 401 para embeddings |

A fábrica de modelos é `src/llm/provedores.py`: trocar de modelo é trocar o par
`(provedor, modelo)`, e a chain não muda.

A conta gratuita da Groq tem cota de 200 mil tokens **por dia** por modelo, e uma rodada
completa de avaliação passa disso. Por isso `python -m evals.rodar_tudo` aceita
`--geracao` e `--juiz`: quando a Groq está sem cota, legado, iterações e testes de
segurança rodam todos no mesmo modelo alternativo, e a linha abaixo das tabelas informa
qual modelo respondeu e qual julgou.

## Parâmetros

| Parâmetro | Sprint 3 | Sprint 4 | Por quê |
|---|---:|---:|---|
| `temperature` | 0,4 | **0** | Com RAG a resposta tem que sair dos trechos; amostragem só abre espaço para o modelo "completar" com o que não está lá. |
| `top_p` | 1,0 | 1,0 | Com temperatura 0 o `top_p` não muda nada; fica em 1 para só uma variável controlar a amostragem. |
| `max_tokens` | 450 | 450 | Cabe uma resposta de 2 a 4 frases com citações; com 250 a lista cortava no meio. |
| `k` (top-k) | 5 frases | **4 chunks** | A iteração 1 usa k = 3 com chunks de 1000 caracteres (~3000 caracteres de contexto); com chunks de 500, k = 4 entrega ~2000 caracteres, de mais documentos diferentes, sem inflar o prompt. O efeito aparece na métrica de recuperação (hit@k) das iterações. |
| limiar de relevância | — | **0,45** (calibrável) | Sem limiar, toda pergunta recebe k trechos, mesmo sem nada a ver com a base, e o modelo tenta responder com eles. O valor inicial é calibrado com `python -m evals.calibrar_limiar`, que mede a relevância do melhor trecho nas perguntas com e sem resposta na base, e pode ser trocado pela variável `RAG_LIMIAR`. |
| `reasoning_format` (gpt-oss) | `hidden` | `hidden` | Sem isso o texto vem vazio (Sprint 3). |

**Avaliação.** As notas de faithfulness e answer relevancy vêm da rubrica manual
(`evals/fallback/rubrica_manual.md`) aplicada por LLM-juiz (`evals/fallback_manual.py`),
com temperatura 0 e `max_tokens` 1500 (com 600 a justificativa cortava e o JSON da nota vinha
quebrado). O juiz é o mesmo em todas as linhas da comparação abaixo. Com RAGAS
(`evals.run_iteracoes` e `evals.run_modelos`, ainda disponíveis), o juiz roda com
temperatura 0 e `max_tokens` 2000, porque o faithfulness pede a lista de afirmações em JSON.

## Comparação de modelos

Mesma configuração (iteração 3: `secao_500`, k = 4, limiar 0,45, prompt `rag_v3`),
mesmo eval set e mesmo juiz. Gerado por `python -m evals.rodar_tudo --so modelos`.

<!-- AUTO:modelos -->
| Modelo | temperature | top_p | max_tokens | k | Faithfulness | Answer relevancy | Recusa correta | Latência média | Tokens/turno |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| groq:openai/gpt-oss-20b | 0 | 1 | 450 | 4 | pendente | pendente | pendente | pendente | pendente |
| groq:openai/gpt-oss-120b | 0 | 1 | 450 | 4 | pendente | pendente | pendente | pendente | pendente |
| ollama:gemma4:cloud | 0 | 1 | 450 | 4 | pendente | pendente | pendente | pendente | pendente |
| gemini:gemini-3.1-flash-lite | 0 | 1 | 450 | 4 | pendente | pendente | pendente | pendente | pendente |
<!-- /AUTO:modelos -->

## Chamada multi-provider

`src/llm/multi_provider.py` responde a mesma pergunta com mais de um modelo e mais de
uma versão de prompt, em paralelo, usando **os mesmos trechos recuperados** — assim a
diferença entre as respostas é do modelo e do prompt, não da busca. Combinações padrão:

| Provedor | Modelo | Prompt |
|---|---|---|
| Groq | `openai/gpt-oss-20b` | `rag_v3` |
| Groq | `openai/gpt-oss-20b` | `rag_v2` |
| Ollama Cloud | `gemma4:cloud` | `rag_v3` |

Na interface, aba **Comparar modelos**.
