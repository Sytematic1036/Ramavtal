#!/usr/bin/env python3
"""Demo/test för EXP-002: Heading Search.

Användning:
  python demo.py build          # Bygg berikat index
  python demo.py list           # Lista tillgängliga strategier
  python demo.py search <strategi> <fråga>  # Sök med vald strategi
  python demo.py inspect        # Visa heading-metadata i index

Exempel:
  python demo.py build
  python demo.py search heading "Kvalitet"
  python demo.py search heading_semantic "samarbete"
  python demo.py search hybrid "timpris"
  python demo.py inspect
"""

import sys
import textwrap
from pathlib import Path

# Projektroten
PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))
# Experiment src
sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
from enhanced_index import EnrichedIndex
from search_strategies import get_strategy, list_strategies


def cmd_build():
    print("Bygger berikat index med heading-metadata...\n")
    idx = EnrichedIndex()
    idx.build(config.DOCS_DIR)
    print(f"\nKlart! {len(idx.chunks)} chunks med heading-metadata.")


def cmd_list():
    strategies = list_strategies()
    print("Tillgängliga sökstrategier:\n")
    for s in strategies:
        print(f"  {s['name']:25s} {s['description']}")


def cmd_inspect():
    idx = EnrichedIndex.load()
    if not idx.chunks:
        print("Inget index. Kör: python demo.py build")
        return

    print(f"Index: {len(idx.chunks)} chunks, {len(idx.manifest)} dokument\n")

    # Visa unika rubriker per dokument
    doc_headings: dict[str, set] = {}
    has_metadata = False
    for c in idx.chunks:
        h = c.get("heading", "")
        if h:
            has_metadata = True
            doc_headings.setdefault(c["filename"], set()).add(h)

    if not has_metadata:
        print("OBS: Inga heading-metadata i index.")
        print("Kör 'python demo.py build' för att bygga berikat index.")
        return

    for fname, headings in sorted(doc_headings.items()):
        print(f"  {fname}:")
        for h in sorted(headings):
            print(f"    - {h}")
        print()


def cmd_search(strategy_name: str, query: str):
    idx = EnrichedIndex.load()
    if not idx.chunks:
        print("Inget index. Kör: python demo.py build")
        return

    strategy_fn = get_strategy(strategy_name)
    print(f"Strategi: {strategy_name}")
    print(f"Sökfråga: \"{query}\"\n")

    results = strategy_fn(query, idx)

    if not results:
        print("Inga resultat.")
        return

    print(f"{len(results)} resultat:\n")
    for i, r in enumerate(results, 1):
        heading = r.get("heading", "")
        heading_str = f" [{heading}]" if heading else ""
        score = r.get("score", "")
        score_str = f" (score: {score})" if score else ""

        print(f"--- Resultat {i}{score_str} ---")
        print(f"Källa: {r['filename']}{heading_str} (chunk {r.get('chunk_idx', '?')})")
        print(textwrap.fill(r["text"][:500], width=100))
        print()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "build":
        cmd_build()
    elif cmd == "list":
        cmd_list()
    elif cmd == "inspect":
        cmd_inspect()
    elif cmd == "search":
        if len(sys.argv) < 4:
            print("Användning: python demo.py search <strategi> <fråga>")
            print("Exempel:    python demo.py search heading \"Kvalitet\"")
            sys.exit(1)
        strategy_name = sys.argv[2]
        query = " ".join(sys.argv[3:])
        cmd_search(strategy_name, query)
    else:
        print(f"Okänt kommando: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
