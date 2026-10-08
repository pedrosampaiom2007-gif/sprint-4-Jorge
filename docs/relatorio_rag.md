# Relatório do RAG — Sprint 4

## Base de conhecimento (`data/knowledge_base/`)

| Documento | Origem | Tipo | Acesso |
|---|---|---|---|
| GoodWe — User Manual AC Charger HCA Series (7-22 kW), V1.3 | [goodwe.com](https://en.goodwe.com/Ftp/EN/Downloads/User%20Manual/GW_HCA%20Series_User%20Manual-EN.pdf) | manual de produto | público |
| Secovi-SP — Instalação de carregadores em condomínios: perguntas e respostas (2025) | [secovi.com.br](https://secovi.com.br/wp-content/uploads/2025/02/faq-veiculos-eletricos-20250206.pdf) | FAQ de condomínio | público |
| Secovi-SP — Recarga em condomínios: riscos, segurança e responsabilidades (2026) | [secovi.com.br](https://secovi.com.br/wp-content/uploads/2026/04/20260423-PAULO-REWALD.pdf) | apresentação | público |
| Arval Brasil — Guia do condutor de veículos elétricos (2024) | [arvalbrasil.com.br](https://www.arvalbrasil.com.br/sites/default/files/157/2024/07/GUIA%20DE%20CONDUTORES%20DE%20CARROS%20EL%C3%89TRICOS.pdf) | guia do motorista | público |
| PROMOB-e — Eletropostos: instalação para grandes demandas | [pnme.org.br](https://pnme.org.br/wp-content/uploads/2020/04/guia_promobe_eletroposto_simples_v2.pdf) | guia técnico | público |
| Manual de operação do ChargeGrid Intelligence | equipe | manual de produto | público |
| Tabela tarifária do ChargeGrid | equipe | tabela tarifária | público |
| FAQ de recarga para motoristas | equipe | FAQ | público |
| Modelo de regimento para recarga compartilhada em condomínio | equipe | regimento | público |
| Relatório histórico de operação — base SP2 | equipe, gerado de `Trabalho_Analise_Comercial_SP2.xlsx` | relatório | **gestão** |

Os documentos da equipe só contêm o que já existia no projeto (regras de tarifa,
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

| Iteração | Faithfulness | Ganho | Answer relevancy | Ganho | Recuperação (hit@k) | Citação | Modelo citou [n] | Recusa correta |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Iteração 1 | pendente | — | pendente | — | pendente | pendente | pendente | pendente |
| Iteração 2 | pendente | — | pendente | — | pendente | pendente | pendente | pendente |
| Iteração 3 | pendente | — | pendente | — | pendente | pendente | pendente | pendente |
<!-- /AUTO:iteracoes -->

## Antes e depois

<!-- AUTO:antes_depois -->
| Critério | Sprints 1/2 (versão original) | Sprint 04 (RAG avaliado) |
|---|---|---|
| Recuperação | palavra-chave em 22 frases da planilha SP2 | busca vetorial (nomic-embed-text + ChromaDB) em 10 documentos, com filtro de acesso e limiar |
| Faithfulness (RAGAS) | pendente | pendente |
| Faithfulness por iteração | versão única | it1 pendente → it2 pendente → it3 pendente |
| Answer relevancy (RAGAS) | pendente | pendente |
| Answer relevancy por iteração | versão única | it1 pendente → it2 pendente → it3 pendente |
| Qualidade do contexto recuperado (documento certo entre os trechos) | pendente | pendente |
| Presença de citação de fonte | pendente | pendente |
| Recusa correta (sem resposta na base, fora de escopo, dado restrito) | pendente | pendente |
| Checagens determinísticas OK | pendente | pendente |
| Latência média por turno | pendente | pendente |
| Tokens por turno (média) | pendente | pendente |
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
- Fallback manual: rubrica 0–1 equivalente em `evals/fallback/rubrica_manual.md`.
