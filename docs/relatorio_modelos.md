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
| gemini:gemini-3.1-flash-lite | 0 | 1 | 450 | 4 | 1,000 | 0,738 | 100% | 3,04 s | 2493 |
| groq:openai/gpt-oss-120b | 0 | 1 | 450 | 4 | 1,000 | 0,700 | 100% | 9,30 s | 2463 |
| groq:openai/gpt-oss-20b | 0 | 1 | 450 | 4 | 0,988 | 0,750 | 75% | 9,98 s | 2475 |
| ollama:gemma4:cloud | 0 | 1 | 450 | 4 | 0,988 | 0,738 | 100% | 0,79 s | 2470 |
<!-- /AUTO:modelos -->

**Leitura.** Os quatro modelos ficam praticamente empatados em faithfulness (0,99 a 1,00).
Com o mesmo contexto e o mesmo prompt `rag_v3`, nenhum inventa fora dos trechos. Também
zeram a relevancy nos mesmos 5 casos com resposta na base, que são os casos em que a busca
não trouxe o documento certo. Isso é limite da recuperação, não do modelo. As diferenças:

- **Recusa correta.** O `gpt-oss-20b`, modelo de produção, foi o único que respondeu uma
  das duas perguntas sem resposta na base (75%). Ele montou uma resposta com um trecho do
  guia PROMOB-e que não respondia à pergunta. Os outros três recusaram os quatro casos (100%).
- **Answer relevancy.** O `gpt-oss-20b` teve a maior (0,750) e o `gpt-oss-120b` a menor
  (0,700). O 120b deu mais respostas incompletas, com nota 0,75 em vez de 1.
- **Latência.** Depende mais do provedor: cerca de 9 a 10 s por turno nos dois modelos da
  Groq, cerca de 3 s no Gemini e menos de 1 s no `gemma4:cloud`. Os tokens por turno são
  parecidos (cerca de 2.500), porque o contexto recuperado é o mesmo.

Ressalva: o Gemini também é o juiz da rubrica, então a nota dele pode ter viés de
autoavaliação.

Pelos números, o `gemma4:cloud` tem o melhor equilíbrio: recusa tudo o que deveria recusar,
tem relevancy perto da maior e é o mais rápido. O `gpt-oss-20b` continua como padrão porque
é o modelo das Sprints anteriores e de toda a tabela antes/depois. Trocar o modelo padrão é
só mudar o par `(provedor, modelo)` e fica como próximo passo.

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
