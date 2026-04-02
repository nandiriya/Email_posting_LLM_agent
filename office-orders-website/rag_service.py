import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import faiss
import fitz
import numpy as np
import pdfplumber
from openai import OpenAI
from sentence_transformers import SentenceTransformer


BASE_DIR = Path(__file__).resolve().parent
PDF_DIR = BASE_DIR / "static" / "pdfs"
RAG_STORE_DIR = BASE_DIR / "rag_store"
INDEX_PATH = RAG_STORE_DIR / "office_orders.index"
METADATA_PATH = RAG_STORE_DIR / "office_orders_chunks.json"
MANIFEST_PATH = RAG_STORE_DIR / "office_orders_manifest.json"

DEFAULT_EMBEDDING_MODEL = os.getenv("RAG_EMBED_MODEL", "all-MiniLM-L6-v2")
DEFAULT_CHAT_MODEL = os.getenv("NVIDIA_MODEL", "qwen/qwen3-next-80b-a3b-instruct")
DEFAULT_TOP_K = int(os.getenv("RAG_TOP_K", "5"))
CHUNK_SIZE = int(os.getenv("RAG_CHUNK_SIZE", "220"))
CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", "40"))

_EMBED_MODEL: Optional[SentenceTransformer] = None


@dataclass
class ChunkRecord:
    chunk_id: int
    file_name: str
    pdf_path: str
    page: int
    text: str


def get_embed_model() -> SentenceTransformer:
    global _EMBED_MODEL
    if _EMBED_MODEL is None:
        _EMBED_MODEL = SentenceTransformer(DEFAULT_EMBEDDING_MODEL)
    return _EMBED_MODEL


def extract_pdf_pages(pdf_path: Path) -> List[Dict[str, Any]]:
    pages: List[Dict[str, Any]] = []

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for idx, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                if text.strip():
                    pages.append({"page": idx, "text": text.strip()})
    except Exception:
        pages = []

    if pages:
        return pages

    with fitz.open(pdf_path) as doc:
        for idx, page in enumerate(doc, start=1):
            text = page.get_text("text") or ""
            if text.strip():
                pages.append({"page": idx, "text": text.strip()})

    return pages


def chunk_words(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    words = text.split()
    if not words:
        return []

    step = max(1, chunk_size - overlap)
    chunks: List[str] = []

    for start in range(0, len(words), step):
        chunk = " ".join(words[start : start + chunk_size]).strip()
        if chunk:
            chunks.append(chunk)
        if start + chunk_size >= len(words):
            break

    return chunks


def build_pdf_manifest(pdf_files: List[Path]) -> List[Dict[str, Any]]:
    manifest: List[Dict[str, Any]] = []
    for pdf_file in pdf_files:
        stat = pdf_file.stat()
        manifest.append(
            {
                "name": pdf_file.name,
                "size": stat.st_size,
                "mtime": int(stat.st_mtime),
            }
        )
    return manifest


class OfficeOrdersRAG:
    def __init__(self) -> None:
        self.index: Optional[faiss.Index] = None
        self.metadata: List[Dict[str, Any]] = []

    def _pdf_files(self) -> List[Path]:
        return sorted(PDF_DIR.glob("*.pdf"))

    def _manifest_matches(self) -> bool:
        if not INDEX_PATH.exists() or not METADATA_PATH.exists() or not MANIFEST_PATH.exists():
            return False

        current_manifest = build_pdf_manifest(self._pdf_files())
        try:
            stored_manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        except Exception:
            return False

        return stored_manifest == current_manifest

    def _save(self, manifest: List[Dict[str, Any]]) -> None:
        RAG_STORE_DIR.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(INDEX_PATH))
        METADATA_PATH.write_text(json.dumps(self.metadata, indent=2, ensure_ascii=False), encoding="utf-8")
        MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    def _load(self) -> bool:
        if not INDEX_PATH.exists() or not METADATA_PATH.exists():
            return False

        self.index = faiss.read_index(str(INDEX_PATH))
        self.metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
        return True

    def ensure_index(self, force_rebuild: bool = False) -> Dict[str, Any]:
        if not force_rebuild and self._manifest_matches():
            if self.index is None or not self.metadata:
                self._load()
            return {
                "status": "ready",
                "pdf_count": len(self._pdf_files()),
                "chunk_count": len(self.metadata),
                "rebuilt": False,
            }

        return self.build_index()

    def build_index(self) -> Dict[str, Any]:
        pdf_files = self._pdf_files()
        manifest = build_pdf_manifest(pdf_files)
        records: List[ChunkRecord] = []

        for pdf_file in pdf_files:
            pages = extract_pdf_pages(pdf_file)
            for page_data in pages:
                for chunk in chunk_words(page_data["text"]):
                    records.append(
                        ChunkRecord(
                            chunk_id=len(records),
                            file_name=pdf_file.name,
                            pdf_path=f"/static/pdfs/{pdf_file.name}",
                            page=page_data["page"],
                            text=chunk,
                        )
                    )

        if not records:
            raise ValueError(f"No readable PDF text found in {PDF_DIR}")

        model = get_embed_model()
        embeddings = model.encode([record.text for record in records], show_progress_bar=False)
        embeddings = np.asarray(embeddings, dtype="float32")
        faiss.normalize_L2(embeddings)

        self.index = faiss.IndexFlatIP(embeddings.shape[1])
        self.index.add(embeddings)
        self.metadata = [record.__dict__ for record in records]
        self._save(manifest)

        return {
            "status": "ready",
            "pdf_count": len(pdf_files),
            "chunk_count": len(records),
            "rebuilt": True,
        }

    def retrieve(self, query: str, top_k: int = DEFAULT_TOP_K) -> List[Dict[str, Any]]:
        self.ensure_index()
        if self.index is None or not self.metadata:
            raise ValueError("RAG index is not available")

        query_embedding = get_embed_model().encode([query])
        query_embedding = np.asarray(query_embedding, dtype="float32")
        faiss.normalize_L2(query_embedding)

        limit = min(max(1, top_k), len(self.metadata))
        scores, indices = self.index.search(query_embedding, limit)

        results: List[Dict[str, Any]] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:
                continue
            item = dict(self.metadata[idx])
            item["score"] = float(score)
            results.append(item)

        return results

    def _answer_with_llm(self, query: str, contexts: List[Dict[str, Any]]) -> str:
        api_key = os.getenv("NVIDIA_API_KEY") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            return self._fallback_answer(contexts)

        base_url = os.getenv("NVIDIA_API_BASE", "https://integrate.api.nvidia.com/v1")
        client = OpenAI(base_url=base_url, api_key=api_key)

        context_blocks = []
        for idx, item in enumerate(contexts, start=1):
            context_blocks.append(
                f"[Source {idx}] File: {item['file_name']} | Page: {item['page']}\n{item['text']}"
            )

        system_prompt = (
            "You are a retrieval assistant for IIIT-Delhi office orders. "
            "Answer only from the provided sources. If the answer is not supported by the sources, "
            "say that the corpus does not contain enough information. Keep the answer concise and factual. "
            "Cite supporting sources inline like [Source 1]."
        )

        user_prompt = (
            f"Question: {query}\n\n"
            f"Sources:\n\n{chr(10).join(context_blocks)}"
        )

        response = client.chat.completions.create(
            model=DEFAULT_CHAT_MODEL,
            temperature=0.1,
            max_tokens=600,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )

        return response.choices[0].message.content.strip()

    def _fallback_answer(self, contexts: List[Dict[str, Any]]) -> str:
        if not contexts:
            return "I could not find relevant office-order content for that question."

        lines = ["I found the following relevant excerpts from the indexed office orders:"]
        for idx, item in enumerate(contexts[:3], start=1):
            snippet = item["text"][:350].replace("\n", " ").strip()
            lines.append(f"[Source {idx}] {item['file_name']} (page {item['page']}): {snippet}")
        lines.append("Set `NVIDIA_API_KEY` to enable synthesized answers grounded in these sources.")
        return "\n\n".join(lines)

    def answer_query(self, query: str, top_k: int = DEFAULT_TOP_K) -> Dict[str, Any]:
        contexts = self.retrieve(query=query, top_k=top_k)
        answer = self._answer_with_llm(query=query, contexts=contexts)
        return {
            "question": query,
            "answer": answer,
            "sources": [
                {
                    "file_name": item["file_name"],
                    "pdf_path": item["pdf_path"],
                    "page": item["page"],
                    "score": round(item["score"], 4),
                    "snippet": item["text"][:500],
                }
                for item in contexts
            ],
        }
