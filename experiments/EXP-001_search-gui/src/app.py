"""EXP-001: Sök-GUI för Ramavtal — FastAPI backend."""

import sys
from pathlib import Path

# Lägg till projektets rot i path så vi kan importera rag_engine/category_classifier
PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from rag_engine import HybridIndex

app = FastAPI(title="Ramavtal Sök-GUI")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

# Ladda index vid uppstart
_index: HybridIndex | None = None


def get_index() -> HybridIndex:
    global _index
    if _index is None:
        _index = HybridIndex.load()
    return _index


class SearchRequest(BaseModel):
    query: str
    top_k: int = 10


class CategoryRequest(BaseModel):
    category: str


@app.get("/", response_class=HTMLResponse)
async def index_page(request: Request):
    idx = get_index()
    has_index = bool(idx.chunks)
    doc_count = len(idx.manifest) if has_index else 0
    chunk_count = len(idx.chunks) if has_index else 0
    return templates.TemplateResponse("index.html", {
        "request": request,
        "has_index": has_index,
        "doc_count": doc_count,
        "chunk_count": chunk_count,
    })


@app.post("/api/search")
async def api_search(req: SearchRequest):
    idx = get_index()
    if not idx.chunks:
        return {"error": "Inget index finns. Kör 'python search.py index' först.", "results": []}

    if not req.query.strip():
        return {"error": "Ange en sökfråga.", "results": []}

    results = idx.search(req.query, top_k=req.top_k)
    return {"results": results}


@app.post("/api/kategori")
async def api_kategori(req: CategoryRequest):
    idx = get_index()
    if not idx.chunks:
        return {"error": "Inget index finns. Kör 'python search.py index' först.", "results": []}

    if not req.category.strip():
        return {"error": "Ange en kategori.", "results": []}

    try:
        from category_classifier import search_by_category
        results = search_by_category(req.category, idx)
        return {"results": results}
    except Exception as e:
        error_msg = str(e)
        if "ANTHROPIC_API_KEY" in error_msg or "api_key" in error_msg.lower():
            return {"error": "ANTHROPIC_API_KEY saknas. Sätt miljövariabeln för att använda kategorisökning.", "results": []}
        return {"error": f"Fel vid kategorisökning: {error_msg}", "results": []}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=5024)
