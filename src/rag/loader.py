"""
Carrega a base de conhecimento (data/knowledge_base/) como Documents.

- PDF: PyMuPDFLoader, um Document por pagina. Titulo, tipo, nivel de acesso e
  link de origem vem de data/knowledge_base/fontes.json. A secao citada e a
  pagina ("p. 12").
- Markdown: os documentos escritos pela equipe. O cabecalho YAML (--- ... ---)
  traz os metadados, e cada titulo "## " vira uma secao, que e o que aparece
  na citacao ("Tabela tarifaria do ChargeGrid › Horario de ponta").

Arquivo novo na pasta entra na base sozinho na proxima indexacao.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from langchain_core.documents import Document

RAIZ = Path(__file__).resolve().parent.parent.parent
PASTA_BASE = RAIZ / "data" / "knowledge_base"
ARQUIVO_FONTES = "fontes.json"

_FRONT_MATTER = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_SECAO_MD = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)


def juntar_linhas(texto: str) -> str:
    """PDF diagramado (infografico, slide) sai com uma palavra por linha.
    Quebra simples vira espaco; linha em branco continua separando paragrafo."""
    return re.sub(r"(?<!\n)\n(?!\n)", " ", texto)


def limpar_texto(texto: str) -> str:
    """Desfaz hifenizacao de quebra de linha e normaliza espacos."""
    texto = texto.replace("\x00", " ").replace("­", "")
    texto = re.sub(r"(\w)-\n(\w)", r"\1\2", texto)
    texto = re.sub(r"[ \t ]+", " ", texto)
    texto = re.sub(r" *\n *", "\n", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto.strip()


def _ler_front_matter(texto: str) -> tuple[dict, str]:
    m = _FRONT_MATTER.match(texto)
    if not m:
        return {}, texto
    meta: dict[str, str] = {}
    for linha in m.group(1).splitlines():
        if ":" in linha:
            chave, valor = linha.split(":", 1)
            meta[chave.strip()] = valor.strip().strip('"').strip("'")
    return meta, texto[m.end():]


def _metadados_base(caminho: Path, meta: dict) -> dict:
    return {
        "doc_id": caminho.stem,
        "arquivo": caminho.name,
        "titulo": meta.get("titulo", caminho.stem.replace("_", " ")),
        "tipo": meta.get("tipo", "outro"),
        "acesso": meta.get("acesso", "publico"),
        "idioma": meta.get("idioma", "pt"),
        "url": meta.get("url", ""),
        "autoria": meta.get("autoria", ""),
        "ano": int(meta.get("ano") or 0),
    }


def carregar_pdf(caminho: Path, meta: dict) -> list[Document]:
    from langchain_community.document_loaders import PyMuPDFLoader

    base = _metadados_base(caminho, meta)
    documentos = []
    for pagina in PyMuPDFLoader(str(caminho)).load():
        texto = limpar_texto(juntar_linhas(limpar_texto(pagina.page_content)))
        if len(texto) < 40:
            continue
        numero = int(pagina.metadata.get("page", 0)) + 1
        documentos.append(
            Document(page_content=texto, metadata={**base, "secao": f"p. {numero}", "pagina": numero})
        )
    return documentos


def carregar_markdown(caminho: Path) -> list[Document]:
    meta, corpo = _ler_front_matter(caminho.read_text(encoding="utf-8"))
    base = _metadados_base(caminho, meta)
    titulos = list(_SECAO_MD.finditer(corpo))
    documentos = []
    for i, titulo in enumerate(titulos):
        fim = titulos[i + 1].start() if i + 1 < len(titulos) else len(corpo)
        texto = limpar_texto(corpo[titulo.end():fim])
        if texto:
            documentos.append(
                Document(page_content=texto, metadata={**base, "secao": titulo.group(1), "pagina": 0})
            )
    if not titulos and corpo.strip():
        documentos.append(Document(page_content=limpar_texto(corpo), metadata={**base, "secao": "texto", "pagina": 0}))
    return documentos


def carregar_base(pasta: Path = PASTA_BASE) -> list[Document]:
    """Todos os documentos da base, na ordem alfabetica dos arquivos."""
    fontes_path = pasta / ARQUIVO_FONTES
    fontes = json.loads(fontes_path.read_text(encoding="utf-8")) if fontes_path.exists() else {}
    documentos: list[Document] = []
    for caminho in sorted(pasta.iterdir()):
        sufixo = caminho.suffix.lower()
        if sufixo == ".pdf":
            documentos.extend(carregar_pdf(caminho, fontes.get(caminho.name, {})))
        elif sufixo in (".md", ".txt"):
            documentos.extend(carregar_markdown(caminho))
    if not documentos:
        raise FileNotFoundError(f"Nenhum documento em {pasta}")
    return documentos


def resumo_base(documentos: list[Document]) -> list[dict]:
    """Uma linha por arquivo: titulo, tipo, acesso, unidades (paginas/secoes) e tamanho."""
    linhas: dict[str, dict] = {}
    for d in documentos:
        item = linhas.setdefault(d.metadata["arquivo"], {
            "arquivo": d.metadata["arquivo"], "titulo": d.metadata["titulo"],
            "tipo": d.metadata["tipo"], "acesso": d.metadata["acesso"],
            "unidades": 0, "caracteres": 0,
        })
        item["unidades"] += 1
        item["caracteres"] += len(d.page_content)
    return list(linhas.values())
