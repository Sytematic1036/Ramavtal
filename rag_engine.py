import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path

import numpy as np
import pdfplumber
from docx import Document
from sentence_transformers import SentenceTransformer

import config


# ---------------------------------------------------------------------------
# Document loading
# ---------------------------------------------------------------------------

def load_pdf(path: Path) -> str:
    text_parts = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n".join(text_parts)


def load_docx(path: Path) -> str:
    doc = Document(str(path))
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def load_document(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".pdf":
        return load_pdf(path)
    elif ext == ".docx":
        return load_docx(path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")


def load_documents(folder: Path) -> list[dict]:
    docs = []
    for f in sorted(folder.iterdir()):
        if f.suffix.lower() in config.SUPPORTED_EXTENSIONS:
            text = load_document(f)
            if text.strip():
                docs.append({"filename": f.name, "text": text})
    return docs


# ---------------------------------------------------------------------------
# Chunking – sentence-aware
# ---------------------------------------------------------------------------

_SENTENCE_RE = re.compile(r'(?<=[.!?])\s+')


def chunk_text(text: str, chunk_size: int = config.CHUNK_SIZE,
               overlap: int = config.CHUNK_OVERLAP) -> list[str]:
    sentences = _SENTENCE_RE.split(text)
    chunks: list[str] = []
    current_words: list[str] = []

    for sentence in sentences:
        words = sentence.split()
        if not words:
            continue

        if len(current_words) + len(words) > chunk_size and current_words:
            chunks.append(" ".join(current_words))
            # keep overlap words from end
            current_words = current_words[-overlap:] if overlap else []

        current_words.extend(words)

    if current_words:
        chunks.append(" ".join(current_words))

    return chunks


# ---------------------------------------------------------------------------
# Swedish Embedder (KBLab)
# ---------------------------------------------------------------------------

class SwedishEmbedder:
    def __init__(self):
        print(f"Laddar embedding-modell: {config.EMBEDDING_MODEL}...")
        self._model = SentenceTransformer(config.EMBEDDING_MODEL)

    def embed(self, texts: list[str]) -> np.ndarray:
        return self._model.encode(texts, show_progress_bar=True,
                                  convert_to_numpy=True)


# ---------------------------------------------------------------------------
# BM25 (Okapi BM25, pure Python)
# ---------------------------------------------------------------------------

_TOKEN_RE = re.compile(r'\w+', re.UNICODE)


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


class BM25:
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self._doc_freqs: dict[str, int] = {}
        self._doc_lens: list[int] = []
        self._avg_dl: float = 0.0
        self._tf: list[Counter] = []
        self._n_docs: int = 0

    def fit(self, texts: list[str]):
        self._tf = []
        self._doc_lens = []
        df: dict[str, int] = {}

        for text in texts:
            tokens = _tokenize(text)
            tf = Counter(tokens)
            self._tf.append(tf)
            self._doc_lens.append(len(tokens))
            for term in set(tokens):
                df[term] = df.get(term, 0) + 1

        self._doc_freqs = df
        self._n_docs = len(texts)
        self._avg_dl = sum(self._doc_lens) / max(self._n_docs, 1)

    def search(self, query: str, top_k: int = 20) -> list[tuple[int, float]]:
        query_tokens = _tokenize(query)
        scores = [0.0] * self._n_docs

        for term in query_tokens:
            if term not in self._doc_freqs:
                continue
            df = self._doc_freqs[term]
            idf = math.log((self._n_docs - df + 0.5) / (df + 0.5) + 1.0)

            for i, tf in enumerate(self._tf):
                if term not in tf:
                    continue
                freq = tf[term]
                dl = self._doc_lens[i]
                numerator = freq * (self.k1 + 1)
                denominator = freq + self.k1 * (1 - self.b + self.b * dl / self._avg_dl)
                scores[i] += idf * numerator / denominator

        ranked = sorted(enumerate(scores), key=lambda x: -x[1])
        return [(i, s) for i, s in ranked[:top_k] if s > 0]


# ---------------------------------------------------------------------------
# Reciprocal Rank Fusion
# ---------------------------------------------------------------------------

def rrf_fuse(ranked_lists: list[list[tuple[int, float]]],
             k: int = 60) -> list[tuple[int, float]]:
    scores: dict[int, float] = {}
    for ranked in ranked_lists:
        for rank, (doc_id, _) in enumerate(ranked):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores.items(), key=lambda x: -x[1])


# ---------------------------------------------------------------------------
# File hashing
# ---------------------------------------------------------------------------

def _file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(8192), b""):
            h.update(block)
    return h.hexdigest()


def compute_file_hashes(docs_dir: Path) -> dict[str, str]:
    hashes = {}
    for f in sorted(docs_dir.iterdir()):
        if f.suffix.lower() in config.SUPPORTED_EXTENSIONS:
            hashes[f.name] = _file_hash(f)
    return hashes


# ---------------------------------------------------------------------------
# HybridIndex – core class
# ---------------------------------------------------------------------------

class HybridIndex:
    def __init__(self):
        self.chunks: list[dict] = []       # [{text, filename, chunk_idx}]
        self.embeddings: np.ndarray | None = None
        self.manifest: dict = {}           # {filename: {hash, chunk_start, chunk_end}}
        self.bm25 = BM25()
        self._embedder: SwedishEmbedder | None = None

    def _get_embedder(self) -> SwedishEmbedder:
        if self._embedder is None:
            self._embedder = SwedishEmbedder()
        return self._embedder

    # --- Build / Reindex ---------------------------------------------------

    def build(self, docs_dir: Path):
        docs = load_documents(docs_dir)
        file_hashes = compute_file_hashes(docs_dir)

        self.chunks = []
        self.manifest = {}

        for doc in docs:
            text_chunks = chunk_text(doc["text"])
            start = len(self.chunks)
            for i, c in enumerate(text_chunks):
                self.chunks.append({
                    "text": c,
                    "filename": doc["filename"],
                    "chunk_idx": i,
                })
            end = len(self.chunks)
            self.manifest[doc["filename"]] = {
                "hash": file_hashes.get(doc["filename"], ""),
                "chunk_start": start,
                "chunk_end": end,
            }

        print(f"Skapade {len(self.chunks)} chunks från {len(docs)} dokument.")

        embedder = self._get_embedder()
        texts = [c["text"] for c in self.chunks]
        self.embeddings = embedder.embed(texts)

        self.bm25.fit(texts)
        self.save()
        print("Index sparat.")

    def needs_reindex(self, docs_dir: Path) -> tuple[bool, list[str], list[str], list[str]]:
        current = compute_file_hashes(docs_dir)
        old_files = set(self.manifest.keys())
        new_files = set(current.keys())

        added = sorted(new_files - old_files)
        removed = sorted(old_files - new_files)
        changed = sorted(
            f for f in old_files & new_files
            if current[f] != self.manifest[f]["hash"]
        )

        needs = bool(added or removed or changed)
        return needs, added, changed, removed

    def reindex(self, docs_dir: Path):
        needs, added, changed, removed = self.needs_reindex(docs_dir)
        if not needs:
            print("Index är redan uppdaterat.")
            return

        if added:
            print(f"  Nya filer: {', '.join(added)}")
        if changed:
            print(f"  Ändrade filer: {', '.join(changed)}")
        if removed:
            print(f"  Borttagna filer: {', '.join(removed)}")

        files_to_remove = set(removed) | set(changed)
        files_to_add = set(added) | set(changed)

        # Remove chunks for deleted/changed files
        if files_to_remove:
            keep_indices = [
                i for i, c in enumerate(self.chunks)
                if c["filename"] not in files_to_remove
            ]
            self.chunks = [self.chunks[i] for i in keep_indices]
            if self.embeddings is not None and keep_indices:
                self.embeddings = self.embeddings[keep_indices]
            elif not keep_indices:
                self.embeddings = None

            for fname in files_to_remove:
                self.manifest.pop(fname, None)

        # Add chunks for new/changed files
        if files_to_add:
            file_hashes = compute_file_hashes(docs_dir)
            embedder = self._get_embedder()
            new_chunk_texts = []

            for fname in sorted(files_to_add):
                fpath = docs_dir / fname
                text = load_document(fpath)
                text_chunks = chunk_text(text)
                start = len(self.chunks)
                for i, c in enumerate(text_chunks):
                    self.chunks.append({
                        "text": c,
                        "filename": fname,
                        "chunk_idx": i,
                    })
                    new_chunk_texts.append(c)
                end = len(self.chunks)
                self.manifest[fname] = {
                    "hash": file_hashes[fname],
                    "chunk_start": start,
                    "chunk_end": end,
                }

            new_embeddings = embedder.embed(new_chunk_texts)
            if self.embeddings is not None and len(self.embeddings) > 0:
                self.embeddings = np.vstack([self.embeddings, new_embeddings])
            else:
                self.embeddings = new_embeddings

            print(f"  Genererade {len(new_chunk_texts)} nya chunks.")

        # Rebuild BM25 (fast)
        self.bm25.fit([c["text"] for c in self.chunks])

        # Update chunk_start/chunk_end in manifest
        self._rebuild_manifest_ranges()

        self.save()
        print(f"Index uppdaterat: {len(self.chunks)} chunks totalt.")

    def _rebuild_manifest_ranges(self):
        ranges: dict[str, list[int]] = {}
        for i, c in enumerate(self.chunks):
            fname = c["filename"]
            if fname not in ranges:
                ranges[fname] = [i, i + 1]
            else:
                ranges[fname][1] = i + 1
        for fname, (start, end) in ranges.items():
            if fname in self.manifest:
                self.manifest[fname]["chunk_start"] = start
                self.manifest[fname]["chunk_end"] = end

    # --- Search ------------------------------------------------------------

    def search(self, query: str, top_k: int = 20) -> list[dict]:
        if not self.chunks or self.embeddings is None:
            return []

        # Semantic search
        embedder = self._get_embedder()
        q_emb = embedder.embed([query])[0]
        norms = np.linalg.norm(self.embeddings, axis=1) * np.linalg.norm(q_emb)
        norms = np.where(norms == 0, 1, norms)
        cosine_scores = self.embeddings @ q_emb / norms
        sem_ranked = sorted(enumerate(cosine_scores.tolist()),
                            key=lambda x: -x[1])[:top_k * 2]

        # BM25 search
        bm25_ranked = self.bm25.search(query, top_k=top_k * 2)

        # RRF fusion
        fused = rrf_fuse([sem_ranked, bm25_ranked], k=60)

        results = []
        for idx, score in fused[:top_k]:
            chunk = self.chunks[idx]
            results.append({
                "text": chunk["text"],
                "filename": chunk["filename"],
                "chunk_idx": chunk["chunk_idx"],
                "score": round(score, 4),
            })
        return results

    # --- Persistence -------------------------------------------------------

    def save(self):
        config.INDEX_DIR.mkdir(exist_ok=True)

        with open(config.INDEX_DIR / "manifest.json", "w", encoding="utf-8") as f:
            json.dump(self.manifest, f, ensure_ascii=False, indent=2)

        with open(config.INDEX_DIR / "chunks.json", "w", encoding="utf-8") as f:
            json.dump(self.chunks, f, ensure_ascii=False, indent=2)

        if self.embeddings is not None:
            np.save(config.INDEX_DIR / "embeddings.npy", self.embeddings)

    @classmethod
    def load(cls) -> "HybridIndex":
        idx = cls()

        manifest_path = config.INDEX_DIR / "manifest.json"
        chunks_path = config.INDEX_DIR / "chunks.json"
        emb_path = config.INDEX_DIR / "embeddings.npy"

        if not manifest_path.exists():
            return idx

        with open(manifest_path, "r", encoding="utf-8") as f:
            idx.manifest = json.load(f)

        with open(chunks_path, "r", encoding="utf-8") as f:
            idx.chunks = json.load(f)

        if emb_path.exists():
            idx.embeddings = np.load(emb_path)

        # Rebuild BM25 from chunk texts
        if idx.chunks:
            idx.bm25.fit([c["text"] for c in idx.chunks])

        return idx
