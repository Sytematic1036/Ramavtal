#!/usr/bin/env python3
"""Demo/test för EXP-003: Prompt-driven Search.

Användning:
  python demo.py list                              # Lista prompter
  python demo.py show <prompt>                     # Visa prompt-definition
  python demo.py search <prompt> <fråga>           # Kör prompt-sökning

Exempel:
  python demo.py list
  python demo.py show kvalitetssäkring
  python demo.py search kvalitetssäkring "kvalitetskontroll"
  python demo.py search miljökrav "kemiska produkter"
  python demo.py search säkerhet "skyddsronder"
"""

import sys
import textwrap
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
EXP002_SRC = PROJECT_ROOT / "experiments" / "EXP-002_heading-search" / "src"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(EXP002_SRC))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from prompt_engine import list_prompts, load_prompt, search_with_prompt
from enhanced_index import EnrichedIndex


def cmd_list():
    prompts = list_prompts()
    if not prompts:
        print("Inga prompter hittades.")
        return

    print("Tillgängliga prompt-sökningar:\n")
    for p in prompts:
        print(f"  {p['name']:25s} {p['description']}")
        print(f"  {'':25s} retrieval: {p['retrieval']}")
        print()


def cmd_show(prompt_name: str):
    try:
        definition = load_prompt(prompt_name)
    except FileNotFoundError as e:
        print(f"Fel: {e}")
        return

    print(f"Prompt: {definition['name']}")
    print(f"Retrieval-strategi: {definition['retrieval']}")
    print(f"Threshold: {definition['threshold']}")
    print(f"Max retrieval: {definition['top_k_retrieval']}")
    print(f"Max resultat: {definition['top_k_results']}")
    print(f"\nSökprompt:")
    print(textwrap.indent(definition["prompt"].strip(), "  "))


def cmd_search(prompt_name: str, query: str):
    idx = EnrichedIndex.load()
    if not idx.chunks:
        print("Inget index. Kör EXP-002: python demo.py build")
        return

    definition = load_prompt(prompt_name)
    print(f"Prompt: {definition['name']}")
    print(f"Strategi: {definition['retrieval']}")
    print(f"Sökfråga: \"{query}\"")
    print(f"Hämtar kandidater...\n")

    try:
        results = search_with_prompt(prompt_name, query, idx)
    except Exception as e:
        error_msg = str(e)
        if "api_key" in error_msg.lower() or "ANTHROPIC_API_KEY" in error_msg:
            print("Fel: ANTHROPIC_API_KEY saknas.")
            print("Sätt med: export ANTHROPIC_API_KEY=sk-ant-...")
            return
        raise

    if not results:
        print("Inga relevanta resultat hittades.")
        return

    print(f"{len(results)} resultat:\n")
    for i, r in enumerate(results, 1):
        heading = r.get("heading", "")
        heading_str = f" [{heading}]" if heading else ""

        print(f"--- [{r['relevance']}/10] {r['filename']}{heading_str} ---")
        if r.get("motivering"):
            print(f"Motivering: {r['motivering']}")
        print(textwrap.fill(r["text"][:500], width=100))
        print()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "list":
        cmd_list()
    elif cmd == "show":
        if len(sys.argv) < 3:
            print("Användning: python demo.py show <prompt-namn>")
            sys.exit(1)
        cmd_show(sys.argv[2])
    elif cmd == "search":
        if len(sys.argv) < 4:
            print("Användning: python demo.py search <prompt-namn> <fråga>")
            sys.exit(1)
        prompt_name = sys.argv[2]
        query = " ".join(sys.argv[3:])
        cmd_search(prompt_name, query)
    else:
        print(f"Okänt kommando: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
