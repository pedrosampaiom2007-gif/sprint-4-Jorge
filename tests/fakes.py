"""
Dubles para rodar o pipeline RAG offline nos testes, sem Ollama e sem Groq.

HashEmbeddings e um bag-of-words: cada palavra cai numa posicao do vetor por
hash. Nao entende sinonimo, mas pergunta e trecho com palavras em comum ficam
proximos — o suficiente para testar filtro, limiar, citacao e blindagem.
"""

from __future__ import annotations

import hashlib
import math
import re
import unicodedata

from langchain_core.embeddings import Embeddings

_STOP = {"a", "o", "as", "os", "de", "da", "do", "das", "dos", "e", "em", "no", "na", "um", "uma",
         "para", "por", "com", "que", "qual", "quais", "como", "se", "search_document", "search_query"}


def _palavras(texto: str) -> list[str]:
    t = unicodedata.normalize("NFKD", texto.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return [p for p in re.findall(r"[a-z0-9]+", t) if p not in _STOP and len(p) > 2]


class HashEmbeddings(Embeddings):
    def __init__(self, dim: int = 512) -> None:
        self.dim = dim

    def _vetor(self, texto: str) -> list[float]:
        v = [0.0] * self.dim
        for p in _palavras(texto):
            v[int(hashlib.md5(p.encode()).hexdigest(), 16) % self.dim] += 1.0
        norma = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / norma for x in v]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vetor(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vetor(text)
