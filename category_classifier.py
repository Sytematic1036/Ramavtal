import json

import anthropic

import config

client = anthropic.Anthropic()

SYSTEM_PROMPT = """Du är expert på att analysera svenska upphandlingsdokument och ramavtal.

Din uppgift: Givet en kategori och ett antal textpassager, bedöm hur relevant varje passage är för kategorin.

Svara ALLTID med giltig JSON — en lista med objekt:
[
  {"index": 0, "score": 8, "motivering": "Kort förklaring"},
  {"index": 1, "score": 2, "motivering": "Kort förklaring"},
  ...
]

- "score" är 0-10 där 10 = extremt relevant för kategorin
- Var generös med vad som räknas som relevant — synonymer, relaterade begrepp, implikationer
- Om en passage bara tangentiellt berör kategorin, ge 3-4
- Om den direkt handlar om kategorin, ge 7-10"""


def classify_chunks(chunks: list[dict], category: str) -> list[dict]:
    if not chunks:
        return []

    passages = "\n\n".join(
        f"[{i}] (Källa: {c['filename']})\n{c['text'][:1500]}"
        for i, c in enumerate(chunks)
    )

    prompt = f"""Kategori: "{category}"

Bedöm relevansen (0-10) för varje passage nedan:

{passages}

Svara med JSON-lista. Inkludera alla {len(chunks)} passager."""

    response = client.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = response.content[0].text

    # Parse JSON from response (handle markdown code blocks)
    text = response_text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        text = text.rsplit("```", 1)[0]

    scores = json.loads(text)

    # Merge scores back into chunk dicts
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


def search_by_category(category: str, index) -> list[dict]:
    # Step 1: Hybrid retrieval — top 20 candidates
    candidates = index.search(category, top_k=20)

    if not candidates:
        print("Inga resultat hittades.")
        return []

    print(f"Hittade {len(candidates)} kandidater, klassificerar med Claude...")

    # Step 2: LLM classification
    classified = classify_chunks(candidates, category)

    # Step 3: Filter (score >= 5) and sort
    relevant = [c for c in classified if c.get("relevance", 0) >= 5]
    relevant.sort(key=lambda x: -x["relevance"])

    return relevant
