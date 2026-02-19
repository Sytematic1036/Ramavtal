from pathlib import Path

DOCS_DIR = Path("Docs")
INDEX_DIR = Path(".index")

EMBEDDING_MODEL = "KBLab/sentence-bert-swedish-cased"
CLAUDE_MODEL = "claude-sonnet-4-5-20250929"

CHUNK_SIZE = 400       # ord per chunk
CHUNK_OVERLAP = 50     # ord overlap

SUPPORTED_EXTENSIONS = {".pdf", ".docx"}
