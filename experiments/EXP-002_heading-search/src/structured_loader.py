"""Heading-aware document loading for DOCX and PDF.

Extracts paragraphs with structural metadata:
  - heading: nearest heading above this element
  - heading_level: 1 for top-level, 2 for sub-heading, etc.
  - section_path: ancestor heading chain ["H1", "H1 > H2"]
  - element_type: "heading", "paragraph", "list_item"
"""

import re
from pathlib import Path

import pdfplumber
from docx import Document


def load_docx_structured(path: Path) -> list[dict]:
    """Parse DOCX preserving heading structure via paragraph styles."""
    doc = Document(str(path))
    elements = []
    current_heading = ""
    current_level = 0
    section_stack: list[str] = []

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue

        style_name = para.style.name or ""

        if style_name.startswith("Heading"):
            # Extract level: "Heading 1" -> 1, "Heading 2" -> 2
            level_match = re.search(r'\d+', style_name)
            level = int(level_match.group()) if level_match else 1

            # Trim stack to parent depth, then push current
            section_stack = section_stack[:level - 1]
            section_stack.append(text)

            current_heading = text
            current_level = level

            elements.append({
                "text": text,
                "heading": text,
                "heading_level": level,
                "section_path": section_stack[:],
                "element_type": "heading",
            })
        elif style_name.startswith("List"):
            elements.append({
                "text": text,
                "heading": current_heading,
                "heading_level": current_level,
                "section_path": section_stack[:],
                "element_type": "list_item",
            })
        else:
            elements.append({
                "text": text,
                "heading": current_heading,
                "heading_level": current_level,
                "section_path": section_stack[:],
                "element_type": "paragraph",
            })

    return elements


def load_pdf_structured(path: Path) -> list[dict]:
    """Parse PDF with heuristic heading detection based on font size."""
    elements = []
    current_heading = ""
    section_stack: list[str] = []

    with pdfplumber.open(path) as pdf:
        # Pass 1: find the body font size (most common) across all pages
        size_counts: dict[float, int] = {}
        for page in pdf.pages:
            for char in page.chars:
                s = round(char["size"], 1)
                size_counts[s] = size_counts.get(s, 0) + 1

        if not size_counts:
            return elements

        body_size = max(size_counts, key=size_counts.get)

        # Pass 2: extract text with heading detection
        for page_num, page in enumerate(pdf.pages, start=1):
            words = page.extract_words(extra_attrs=["size", "fontname"])
            if not words:
                continue

            lines = _group_words_into_lines(words)

            for line in lines:
                text = line["text"].strip()
                if not text:
                    continue

                avg_size = line["avg_size"]
                is_heading = (
                    avg_size > body_size + 1.0
                    and len(text) < 150
                )

                if is_heading:
                    section_stack = [text]
                    current_heading = text

                    elements.append({
                        "text": text,
                        "heading": text,
                        "heading_level": 1,
                        "section_path": section_stack[:],
                        "element_type": "heading",
                        "page": page_num,
                    })
                else:
                    # Detect bullet points
                    el_type = "list_item" if _is_bullet(text) else "paragraph"

                    elements.append({
                        "text": text,
                        "heading": current_heading,
                        "heading_level": 1 if current_heading else 0,
                        "section_path": section_stack[:],
                        "element_type": el_type,
                        "page": page_num,
                    })

    return elements


def _group_words_into_lines(words: list[dict], y_tolerance: float = 3.0) -> list[dict]:
    """Group words into lines based on vertical position."""
    if not words:
        return []

    lines = []
    current_line_words = [words[0]]
    current_top = words[0]["top"]

    for w in words[1:]:
        if abs(w["top"] - current_top) <= y_tolerance:
            current_line_words.append(w)
        else:
            lines.append(_make_line(current_line_words))
            current_line_words = [w]
            current_top = w["top"]

    if current_line_words:
        lines.append(_make_line(current_line_words))

    return lines


def _make_line(words: list[dict]) -> dict:
    """Combine words into a single line with averaged font size."""
    text = " ".join(w["text"] for w in words)
    avg_size = sum(w["size"] for w in words) / len(words)
    return {"text": text, "avg_size": avg_size}


_BULLET_RE = re.compile(r'^[\u2022\u2023\u25E6\u2043\u2219•\-–—]\s*')


def _is_bullet(text: str) -> bool:
    return bool(_BULLET_RE.match(text))


def load_document_structured(path: Path) -> list[dict]:
    """Load any supported document with structural metadata."""
    ext = path.suffix.lower()
    if ext == ".pdf":
        return load_pdf_structured(path)
    elif ext == ".docx":
        return load_docx_structured(path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")
