# Relatório do RAG — Sprint 4

## Base de conhecimento (`data/knowledge_base/`)

| Documento | Origem | Tipo | Acesso |
|---|---|---|---|
| GoodWe — User Manual AC Charger HCA Series (7-22 kW), V1.3 | [goodwe.com](https://en.goodwe.com/Ftp/EN/Downloads/User%20Manual/GW_HCA%20Series_User%20Manual-EN.pdf) | manual de produto | público |
| Secovi-SP — Instalação de carregadores em condomínios: perguntas e respostas (2025) | [secovi.com.br](https://secovi.com.br/wp-content/uploads/2025/02/faq-veiculos-eletricos-20250206.pdf) | FAQ de condomínio | público |
| Secovi-SP — Recarga em condomínios: riscos, segurança e responsabilidades (2026) | [secovi.com.br](https://secovi.com.br/wp-content/uploads/2026/04/20260423-PAULO-REWALD.pdf) | apresentação | público |
| Arval Brasil — Guia do condutor de veículos elétricos (2024) | [arvalbrasil.com.br](https://www.arvalbrasil.com.br/sites/default/files/157/2024/07/GUIA%20DE%20CONDUTORES%20DE%20CARROS%20EL%C3%89TRICOS.pdf) | guia do motorista | público |
| PROMOB-e — Eletropostos: instalação para grandes demandas | [pnme.org.br](https://pnme.org.br/wp-content/uploads/2020/04/guia_promobe_eletroposto_simples_v2.pdf) | guia técnico | público |
| Manual de operação do ChargeGrid Intelligence | autor do projeto | manual de produto | público |
| Tabela tarifária do ChargeGrid | autor do projeto | tabela tarifária | público |
| FAQ de recarga para motoristas | autor do projeto | FAQ | público |
| Modelo de regimento para recarga compartilhada em condomínio | autor do projeto | regimento | público |
| Relatório histórico de operação — base SP2 | autor do projeto, gerado de `Trabalho_Analise_Comercial_SP2.xlsx` | relatório | **gestão** |

Os documentos escritos para o projeto só contêm o que já existia no projeto (regras de tarifa,
cashback e DLB do sistema, números da planilha SP2). O regimento é um **modelo** para o
piloto em condomínios e diz isso no próprio texto.

## Pipeline

| Etapa | Arquivo | Decisão |
|---|---|---|
| Load | `src/rag/loader.py` | `PyMuPDFLoader` (uma página por Document); Markdown com cabeçalho YAML, uma seção por `##` |
| Chunking | `src/rag/chunking.py` | `RecursiveCharacterTextSplitter`, separadores `\n\n`, `\n`, `. `, ` ` |
| Embeddings | `src/rag/embeddings.py` | `OllamaEmbeddings(model="nomic-embed-text")` com prefixos `search_document:` / `search_query:` |
| Vector store | `src/rag/vector_store.py` | `langchain_chroma.Chroma` persistente em `data/chroma/`, distância cosseno, ids estáveis |
| Retriever | `src/rag/retriever.py` | similaridade com filtro `where={"acesso": "publico"}`, limiar 0,45, k = 4; `RetrieverChargeGrid` (BaseRetriever) |
| Blindagem | `src/rag/blindagem.py` | troca frase dirigida ao assistente por aviso antes do contexto |
| Prompt | `prompts/rag/rag_v*.md`, `src/rag/prompt_rag.py` | versionado, trechos numerados com documento e seção |
| Citação | `src/rag/citacao.py` | linha "Fontes:" garantida em código |

## Estratégias de chunking

| Estratégia | chunk_size | overlap | Cabeçalho | Chunks | Média de caracteres |
|---|---:|---:|---|---:|---:|
| `fixo_1000` | 1000 | 150 | não | 295 | 591 |
| `secao_500` | 500 | 75 | título — seção | 493 | 436 |

A comparação com RAGAS está nas iterações abaixo: a iteração 1 usa `fixo_1000` e as
iterações 2 e 3, `secao_500`.

## Scores por iteração

<!-- AUTO:iteracoes -->
- **Iteração 1:** chunk fixo 1000/150, prompt rag_v1, k=3, sem guardas em código.
- **Iteração 2:** chunk por seção 500/75 com cabeçalho, prompt rag_v2 (grounding + citação), limiar 0,45, recusa em código.
- **Iteração 3:** prompt rag_v3 com exemplos + reescrita da pergunta encadeada.

| Iteração | Faithfulness | Answer relevancy | Recuperação (hit@k) | Citação | Recusa correta | Checagens OK |
|---|---:|---:|---:|---:|---:|---:|
| Sprints 1/2 (antes) | 0,20 | 0,91 | 10% | 0% | 100% | 46% |
| Iteração 1 | 1,00 | 0,76 | 75% | 0% | 100% | 67% |
| Iteração 2 | pendente | pendente | 85% | 100% | 100% | 71% |
| Iteração 3 | pendente | pendente | pendente | pendente | pendente | pendente |

**Leitura parcial.** Do chatbot antigo para o RAG, a fidelidade sobe de 0,20 para 1,00: o
legado respondia "de cabeça" e quase nada do que dizia estava nos documentos. A relevância
cai de 0,91 para 0,76 porque, na iteração 1, quando a busca não acha o documento certo o
modelo recusa em vez de inventar — e recusa a uma pergunta que tinha resposta conta como
relevância 0. A iteração 2 ataca exatamente isso: a recuperação sobe de 75% para 85% com o
chunk por seção, e a citação de fonte vai de 0% para 100%.
<!-- /AUTO:iteracoes -->

## Antes e depois

<!-- AUTO:antes_depois -->
| Critério | Sprints 1/2 (versão original) | Sprint 04 — iteração 1 | Sprint 04 — iteração 2 | Sprint 04 — iteração 3 |
|---|---|---|---|---|
| Recuperação | palavra-chave em 22 frases da planilha SP2 | busca vetorial, chunk fixo 1000 | busca vetorial, chunk por seção 500 | busca vetorial + reescrita da pergunta |
| Faithfulness (rubrica) | 0,20 | 1,00 | pendente | pendente |
| Answer relevancy (rubrica) | 0,91 | 0,76 | pendente | pendente |
| Qualidade do contexto (documento certo entre os trechos) | 10% trouxe algum contexto | 75% | 85% | pendente |
| Presença de citação de fonte | 0% | 0% | 100% | pendente |
| Recusa correta (sem resposta na base, fora de escopo, dado restrito) | 100% | 100% | 100% | pendente |
| Checagens determinísticas OK | 46% | 67% | 71% | pendente |
| Latência média por turno | 0,59 s | 10,42 s* | 6,24 s | pendente |
| Tokens por turno (média) | 1289 | 2501 | 1842 | pendente |

_Resultado PARCIAL. Modelo que respondeu: groq:openai/gpt-oss-20b; faithfulness e answer
relevancy pela rubrica de fallback (`evals/fallback/rubrica_manual.md`) aplicada por LLM-juiz
groq:openai/gpt-oss-120b. Sprints 1/2 e iteração 1: execução de 09/10 (iteração 1 com 17
de 20 casos avaliados pelo juiz; as recusas a perguntas com resposta na base receberam
relevancy 0, como manda a rubrica). Iteração 2: métricas sem juiz da execução de 08/10, que
gerou as 24 respostas; as notas do juiz não saíram porque a cota diária da Groq acabou.
\* latência da iteração 1 inflada pela espera do limite de requisições por minuto. Esta
tabela é substituída automaticamente quando `python -m evals.rodar_tudo` terminar._
<!-- /AUTO:antes_depois -->

## Guardrails do RAG

| Risco | Proteção | Onde |
|---|---|---|
| Responder sem base | recusa em código quando nenhum trecho passa do limiar; prompt manda responder só com o contexto | `src/assistente.py`, `prompts/rag/rag_v2.md` |
| Não citar fonte | linha "Fontes:" acrescentada em código; interface mostra cada trecho | `src/rag/citacao.py`, `app/web.py` |
| Pergunta fora do contexto | recusa por frase fixa; assunto perigoso barrado antes da busca | `src/guardrails/scope_validator.py` |
| Prompt injection na pergunta | 5 camadas da Sprint 3 | `src/guardrails/moderation.py` |
| Prompt injection via documento | blindagem dos trechos + regra no prompt + guarda de saída | `src/rag/blindagem.py` |
| Especificação de produto inventada | regra no prompt (só o que está escrito num trecho) + caso no eval | `prompts/rag/rag_v2.md` |
| Vazamento de dado de gestão | filtro de metadado `acesso` na busca | `src/rag/retriever.py` |

<!-- AUTO:seguranca -->
| Teste | Resultado |
|---|---|
| Injeção via documento | pendente |
| Bateria da Sprint 3 (24 casos, 12 ataques) | pendente |
<!-- /AUTO:seguranca -->

## Avaliação

- RAGAS: `faithfulness` e `answer_relevancy`, juiz `groq:openai/gpt-oss-120b`
  (temperatura 0), embeddings `nomic-embed-text`. Roda nos casos com documento
  esperado que passaram pelo modelo.
- Sem juiz: recuperação (documento esperado entre os trechos), presença de citação
  na resposta final, se o próprio modelo citou `[n]` (sem contar a linha que o código
  acrescenta), recusa correta e checagens determinísticas.
- Fallback: rubrica 0–1 equivalente em `evals/fallback/rubrica_manual.md`, aplicada a
  todos os casos com resposta na base. `python -m evals.rodar_tudo` aplica a rubrica com o
  LLM-juiz `groq:openai/gpt-oss-120b` (temperatura 0) e grava a nota e a justificativa de
  cada caso em `evals/resultados/*.json`; `python -m evals.fallback_manual exportar`
  gera uma planilha para revisar ou refazer as notas à mão. Caso que tinha resposta na
  base mas não foi respondido (recusa, erro) recebe faithfulness 1 e answer relevancy 0,
  conforme a rubrica.
