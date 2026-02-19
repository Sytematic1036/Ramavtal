"""Extensible search strategy registry.

Each strategy is a callable:
    strategy(query: str, index, **kwargs) -> list[dict]

Register new strategies with @register_strategy("name").
Adding a new strategy = adding ONE function. Nothing else changes.
"""

import re
from typing import Callable

_STRATEGIES: dict[str, dict] = {}


def register_strategy(name: str, description: str = ""):
    """Decorator to register a named search strategy."""
    def decorator(fn: Callable) -> Callable:
        _STRATEGIES[name] = {
            "fn": fn,
            "description": description or fn.__doc__ or "",
        }
        return fn
    return decorator


def get_strategy(name: str) -> Callable:
    """Get a strategy function by name."""
    if name not in _STRATEGIES:
        available = ", ".join(sorted(_STRATEGIES))
        raise ValueError(f"Okänd strategi '{name}'. Tillgängliga: {available}")
    return _STRATEGIES[name]["fn"]


def list_strategies() -> list[dict]:
    """List all registered strategies with name and description."""
    return [
        {"name": name, "description": info["description"]}
        for name, info in sorted(_STRATEGIES.items())
    ]


# -----------------------------------------------------------------------
# Built-in strategies
# -----------------------------------------------------------------------

@register_strategy("hybrid", "Standard BM25 + semantisk sökning (RRF)")
def strategy_hybrid(query: str, index, top_k: int = 10, **kwargs) -> list[dict]:
    """Befintlig hybrid-sökning — BM25 + semantic + RRF fusion."""
    return index.search(query, top_k=top_k)


@register_strategy("heading", "Stycken under rubriker som matchar nyckelord")
def strategy_heading(query: str, index, top_k: int = 20, **kwargs) -> list[dict]:
    """Hitta alla chunks vars rubrik (heading) innehåller sökfrågan.

    Returnerar hela stycken under matchande rubriker, sorterade
    efter dokument och position.
    """
    pattern = re.compile(re.escape(query), re.IGNORECASE)

    matches = []
    for chunk in index.chunks:
        heading = chunk.get("heading", "")
        if heading and pattern.search(heading):
            # Inkludera bara body-text, inte rubrikerna själva
            if chunk.get("element_type") != "heading":
                matches.append({
                    **chunk,
                    "score": 1.0,
                    "match_type": "heading_keyword",
                })

    matches.sort(key=lambda c: (c["filename"], c.get("chunk_idx", 0)))
    return matches[:top_k]


@register_strategy("heading_semantic", "Semantisk rubrik-match → alla stycken under")
def strategy_heading_semantic(query: str, index, top_k: int = 20, **kwargs) -> list[dict]:
    """Hitta rubriker semantiskt lika sökfrågan, returnera alla stycken under dem.

    1. Kör hybrid-sökning för att hitta top-kandidater
    2. Samla unika rubriker från dessa
    3. Returnera alla chunks under de rubrikerna
    """
    # Steg 1: Hitta semantiskt relevanta chunks
    candidates = index.search(query, top_k=top_k * 3)

    # Steg 2: Samla unika rubriker
    top_headings = set()
    for c in candidates:
        h = c.get("heading", "")
        if h:
            top_headings.add(h)

    if not top_headings:
        return candidates[:top_k]

    # Steg 3: Returnera alla body-chunks under de rubrikerna
    results = []
    for chunk in index.chunks:
        if chunk.get("heading") in top_headings and chunk.get("element_type") != "heading":
            results.append({
                **chunk,
                "score": 1.0,
                "match_type": "heading_semantic",
            })

    results.sort(key=lambda c: (c["filename"], c.get("chunk_idx", 0)))
    return results[:top_k]


@register_strategy("section_path", "Stycken vars sektion matchar nyckelord")
def strategy_section_path(query: str, index, top_k: int = 20, **kwargs) -> list[dict]:
    """Sök i section_path — matchar hela sektionshierarkin.

    T.ex. query="Leverans" matchar chunks under "3. Leveransvillkor"
    oavsett om det är i heading eller section_path.
    """
    pattern = re.compile(re.escape(query), re.IGNORECASE)

    matches = []
    for chunk in index.chunks:
        section_path = chunk.get("section_path", [])
        if any(pattern.search(s) for s in section_path):
            if chunk.get("element_type") != "heading":
                matches.append({
                    **chunk,
                    "score": 1.0,
                    "match_type": "section_path",
                })

    matches.sort(key=lambda c: (c["filename"], c.get("chunk_idx", 0)))
    return matches[:top_k]
