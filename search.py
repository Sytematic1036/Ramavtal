#!/usr/bin/env python3
"""CLI för semantisk dokumentsökning i ramavtal."""

import argparse
import sys
import textwrap

import config
from rag_engine import HybridIndex


def cmd_index(args):
    """Indexera eller omindexera dokument."""
    if not config.DOCS_DIR.exists():
        print(f"Fel: Mappen '{config.DOCS_DIR}' finns inte.")
        sys.exit(1)

    index = HybridIndex.load()

    if index.chunks:
        needs, added, changed, removed = index.needs_reindex(config.DOCS_DIR)
        if needs:
            print("Inkrementell omindexering...")
            index.reindex(config.DOCS_DIR)
        else:
            print("Index är redan uppdaterat. Använd --force för att bygga om helt.")
            if not args.force:
                return
            print("Bygger om index från grunden...")
            index = HybridIndex()
            index.build(config.DOCS_DIR)
    else:
        print("Bygger nytt index...")
        index.build(config.DOCS_DIR)


def cmd_status(args):
    """Visa indexstatus."""
    index = HybridIndex.load()

    if not index.chunks:
        print("Inget index finns. Kör 'python search.py index' först.")
        return

    print(f"Indexerade dokument: {len(index.manifest)}")
    print(f"Totalt antal chunks: {len(index.chunks)}")
    print()

    for fname, info in sorted(index.manifest.items()):
        n_chunks = info["chunk_end"] - info["chunk_start"]
        print(f"  {fname}: {n_chunks} chunks")

    if config.DOCS_DIR.exists():
        needs, added, changed, removed = index.needs_reindex(config.DOCS_DIR)
        if needs:
            print()
            total = len(added) + len(changed) + len(removed)
            print(f"OBS: {total} fil(er) har ändrats sedan senaste indexering.")
            if added:
                print(f"  Nya: {', '.join(added)}")
            if changed:
                print(f"  Ändrade: {', '.join(changed)}")
            if removed:
                print(f"  Borttagna: {', '.join(removed)}")
            print("Kör 'python search.py index' för att uppdatera.")
        else:
            print("\nIndex är uppdaterat.")


def cmd_search(args):
    """Fri hybrid-sökning."""
    index = HybridIndex.load()

    if not index.chunks:
        print("Inget index finns. Kör 'python search.py index' först.")
        sys.exit(1)

    _check_stale(index)

    query = " ".join(args.query)
    print(f"Söker: \"{query}\"\n")

    results = index.search(query, top_k=args.top_k)

    if not results:
        print("Inga resultat hittades.")
        return

    for i, r in enumerate(results, 1):
        print(f"--- Resultat {i} (score: {r['score']}) ---")
        print(f"Källa: {r['filename']} (chunk {r['chunk_idx']})")
        print(textwrap.fill(r["text"][:500], width=100))
        print()


def cmd_kategori(args):
    """Kategoribaserad sökning med Claude-klassificering."""
    from category_classifier import search_by_category

    index = HybridIndex.load()

    if not index.chunks:
        print("Inget index finns. Kör 'python search.py index' först.")
        sys.exit(1)

    _check_stale(index)

    category = " ".join(args.category)
    print(f"Kategori-sökning: \"{category}\"\n")

    results = search_by_category(category, index)

    if not results:
        print("Inga relevanta passager hittades för denna kategori.")
        return

    print(f"\n{len(results)} relevanta passager:\n")
    for i, r in enumerate(results, 1):
        print(f"--- [{r['relevance']}/10] {r['filename']} (chunk {r['chunk_idx']}) ---")
        if r.get("motivering"):
            print(f"Motivering: {r['motivering']}")
        print(textwrap.fill(r["text"][:500], width=100))
        print()


def _check_stale(index: HybridIndex):
    if config.DOCS_DIR.exists():
        needs, added, changed, removed = index.needs_reindex(config.DOCS_DIR)
        if needs:
            total = len(added) + len(changed) + len(removed)
            print(f"OBS: {total} fil(er) har ändrats sedan senaste indexering. "
                  f"Kör 'python search.py index' för att uppdatera.\n")


def main():
    parser = argparse.ArgumentParser(
        description="Semantisk dokumentsökning för ramavtal"
    )
    sub = parser.add_subparsers(dest="command")

    # index
    p_index = sub.add_parser("index", help="Indexera/omindexera dokument")
    p_index.add_argument("--force", action="store_true",
                         help="Bygg om hela indexet från grunden")

    # status
    sub.add_parser("status", help="Visa indexstatus")

    # search
    p_search = sub.add_parser("search", help="Fri hybrid-sökning")
    p_search.add_argument("query", nargs="+", help="Sökfråga")
    p_search.add_argument("--top-k", type=int, default=10,
                          help="Antal resultat (default: 10)")

    # kategori
    p_cat = sub.add_parser("kategori", help="Kategoribaserad sökning (Claude)")
    p_cat.add_argument("category", nargs="+", help="Kategorinamn")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    commands = {
        "index": cmd_index,
        "status": cmd_status,
        "search": cmd_search,
        "kategori": cmd_kategori,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
