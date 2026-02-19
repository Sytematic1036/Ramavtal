"""Enhanced HybridIndex that preserves heading metadata in chunks.

Extends the existing rag_engine.HybridIndex with structured loading.
After building, chunks carry: heading, section_path, element_type.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

import config
from rag_engine import HybridIndex, chunk_text, compute_file_hashes
from structured_loader import load_document_structured


class EnrichedIndex(HybridIndex):
    """HybridIndex with heading-aware chunks."""

    def build(self, docs_dir: Path):
        """Build index using structured loading — preserves headings."""
        file_hashes = compute_file_hashes(docs_dir)
        self.chunks = []
        self.manifest = {}

        for fpath in sorted(docs_dir.iterdir()):
            if fpath.suffix.lower() not in config.SUPPORTED_EXTENSIONS:
                continue

            elements = load_document_structured(fpath)
            if not elements:
                continue

            # Group elements into chunks while preserving metadata
            enriched_chunks = _elements_to_chunks(elements, fpath.name)

            start = len(self.chunks)
            self.chunks.extend(enriched_chunks)
            end = len(self.chunks)

            self.manifest[fpath.name] = {
                "hash": file_hashes.get(fpath.name, ""),
                "chunk_start": start,
                "chunk_end": end,
            }

        print(f"Skapade {len(self.chunks)} berikade chunks från "
              f"{len(self.manifest)} dokument.")

        # Embed
        embedder = self._get_embedder()
        texts = [c["text"] for c in self.chunks]
        self.embeddings = embedder.embed(texts)

        # BM25
        self.bm25.fit(texts)
        self.save()
        print("Index sparat.")


def _elements_to_chunks(elements: list[dict], filename: str) -> list[dict]:
    """Convert structured elements into size-limited chunks with metadata.

    Groups consecutive elements under the same heading into chunks.
    Respects CHUNK_SIZE while keeping heading metadata.
    """
    chunks = []
    current_words: list[str] = []
    current_heading = ""
    current_section_path: list[str] = []
    current_element_type = "paragraph"
    chunk_idx = 0

    for elem in elements:
        # Skip heading elements as standalone text — their text gets
        # included as context but we primarily index body paragraphs
        if elem["element_type"] == "heading":
            # If we have accumulated text, flush as chunk
            if current_words:
                chunks.append(_make_chunk(
                    current_words, filename, chunk_idx,
                    current_heading, current_section_path, current_element_type,
                ))
                chunk_idx += 1
                current_words = []

            current_heading = elem["heading"]
            current_section_path = elem.get("section_path", [])
            continue

        words = elem["text"].split()
        if not words:
            continue

        # If heading changed, flush current chunk
        if elem.get("heading", "") != current_heading and current_words:
            chunks.append(_make_chunk(
                current_words, filename, chunk_idx,
                current_heading, current_section_path, current_element_type,
            ))
            chunk_idx += 1
            current_words = []
            current_heading = elem.get("heading", "")
            current_section_path = elem.get("section_path", [])

        # If adding these words would exceed chunk size, flush
        if len(current_words) + len(words) > config.CHUNK_SIZE and current_words:
            chunks.append(_make_chunk(
                current_words, filename, chunk_idx,
                current_heading, current_section_path, current_element_type,
            ))
            chunk_idx += 1
            # Keep overlap
            current_words = current_words[-config.CHUNK_OVERLAP:] if config.CHUNK_OVERLAP else []

        current_words.extend(words)
        current_heading = elem.get("heading", current_heading)
        current_section_path = elem.get("section_path", current_section_path)
        current_element_type = elem.get("element_type", "paragraph")

    # Flush remaining
    if current_words:
        chunks.append(_make_chunk(
            current_words, filename, chunk_idx,
            current_heading, current_section_path, current_element_type,
        ))

    return chunks


def _make_chunk(words, filename, chunk_idx, heading, section_path, element_type):
    return {
        "text": " ".join(words),
        "filename": filename,
        "chunk_idx": chunk_idx,
        "heading": heading,
        "section_path": section_path,
        "element_type": element_type,
    }
