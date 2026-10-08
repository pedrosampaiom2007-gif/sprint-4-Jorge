"""
Pipeline RAG da Sprint 4.

    loader.py        PyMuPDFLoader (PDF) + Markdown com front matter -> Documents
    chunking.py      as estrategias de chunking comparadas (RecursiveCharacterTextSplitter)
    embeddings.py    nomic-embed-text via Ollama, com os prefixos de tarefa do modelo
    vector_store.py  ChromaDB persistente em data/chroma/
    blindagem.py     neutraliza instrucao escondida dentro dos documentos
    retriever.py     busca com filtro de acesso, limiar de relevancia e reescrita da pergunta
    prompt_rag.py    prompts RAG versionados (prompts/rag/) e montagem do <contexto>
    citacao.py       garante a citacao de fonte em toda resposta
    config.py        parametros de cada iteracao avaliada
"""
