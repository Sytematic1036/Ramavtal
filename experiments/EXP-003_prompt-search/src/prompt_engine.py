"""Prompt-driven search engine.

Loads search definitions from YAML files and executes them:
  1. Retrieval — via EXP-002 strategy registry
  2. Claude evaluation — scores each candidate against the user's prompt
  3. Filtering — threshold-based

New search = new YAML file. No code changes needed.
"""

import json
import sys
from pathlib import Path

import yaml
import anthropic

# Project and experiment paths
PROJECT_ROOT = Path(__file__).resolve().parents[3]
EXP002_SRC = PROJECT_ROOT / "experiments" / "EXP-002_heading-search" / "src"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(EXP002_SRC))

import config
from search_strategies import get_strategy

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

SYSTEM_PROMPT = """Du är expert på att analysera svenska upphandlingsdokument och ramavtal.

Din uppgift: Givet en sökbeskrivning och ett antal textpassager, bedöm hur relevant varje passage är.

Svara ALLTID med giltig JSON — en lista med objekt:
[
  {{"index": 0, "score": 8, "motivering": "Kort förklaring"}},
  {{"index": 1, "score": 2, "motivering": "Kort förklaring"}},
  ...
]

- "score" är 0-10 där 10 = extremt relevant
- Var generös med vad som räknas som relevant — synonymer, relaterade begrepp, implikationer
- Om en passage bara tangentiellt berör ämnet, ge 3-4
- Om den direkt handlar om ämnet, ge 7-10"""


def load_prompt(name: str) -> dict:
    """Load a prompt definition from YAML file."""
    path = PROMPTS_DIR / f"{name}.yaml"
    if not path.exists():
        available = list_prompts()
        names = ", ".join(p["name"] for p in available) if available else "(inga)"
        raise FileNotFoundError(
            f"Prompt '{name}' hittades inte: {path}\n"
            f"Tillgängliga: {names}"
        )

    with open(path, "r", encoding="utf-8") as f:
        definition = yaml.safe_load(f)

    # Validate required fields
    required = ["name", "prompt"]
    for field in required:
        if field not in definition:
            raise ValueError(f"Prompt-filen '{name}.yaml' saknar fältet '{field}'")

    # Defaults
    definition.setdefault("retrieval", "hybrid")
    definition.setdefault("threshold", 5)
    definition.setdefault("top_k_retrieval", 20)
    definition.setdefault("top_k_results", 10)

    return definition


def list_prompts() -> list[dict]:
    """List all available prompt definitions."""
    if not PROMPTS_DIR.exists():
        return []

    prompts = []
    for f in sorted(PROMPTS_DIR.glob("*.yaml")):
        try:
            with open(f, "r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh)
            prompts.append({
                "name": f.stem,
                "display_name": data.get("name", f.stem),
                "description": data.get("description", ""),
                "retrieval": data.get("retrieval", "hybrid"),
            })
        except Exception:
            continue

    return prompts


def search_with_prompt(prompt_name: str, query: str, index) -> list[dict]:
    """Execute a prompt-driven search.

    1. Load prompt definition (YAML)
    2. Retrieval: run the specified strategy from EXP-002
    3. Claude evaluation: score candidates against the prompt
    4. Filter by threshold, sort by relevance
    """
    definition = load_prompt(prompt_name)

    # Step 1: Retrieval
    strategy_fn = get_strategy(definition["retrieval"])
    candidates = strategy_fn(query, index, top_k=definition["top_k_retrieval"])

    if not candidates:
        return []

    # Step 2: Claude evaluation
    evaluated = _evaluate_with_claude(candidates, query, definition)

    # Step 3: Filter and sort
    threshold = definition["threshold"]
    relevant = [c for c in evaluated if c.get("relevance", 0) >= threshold]
    relevant.sort(key=lambda x: -x["relevance"])

    return relevant[:definition["top_k_results"]]


def _evaluate_with_claude(chunks: list[dict], query: str, definition: dict) -> list[dict]:
    """Send chunks to Claude for evaluation against the prompt definition."""
    client = anthropic.Anthropic()

    passages = "\n\n".join(
        f"[{i}] (Källa: {c['filename']}"
        f"{' | Rubrik: ' + c['heading'] if c.get('heading') else ''})\n"
        f"{c['text'][:1500]}"
        for i, c in enumerate(chunks)
    )

    user_prompt = f"""Sökbeskrivning: "{definition['prompt']}"

Sökfråga från användaren: "{query}"

Bedöm relevansen (0-10) för varje passage nedan mot sökbeskrivningen:

{passages}

Svara med JSON-lista. Inkludera alla {len(chunks)} passager."""

    response = client.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    response_text = response.content[0].text

    # Parse JSON (handle markdown code blocks)
    text = response_text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        text = text.rsplit("```", 1)[0]

    scores = json.loads(text)

    # Merge scores into chunks
    score_map = {item["index"]: item for item in scores}
    results = []
    for i, chunk in enumerate(chunks):
        if i in score_map:
            entry = score_map[i]
            results.append({
                **chunk,
                "relevance": entry["score"],
                "motivering": entry.get("motivering", ""),
            })

    return results
