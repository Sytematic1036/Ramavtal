# EXP-003: Prompt-driven Search

| Fält | Värde |
|------|-------|
| **Status** | EXPERIMENTAL |
| **Target Repo** | https://github.com/Sytematic1036/Ramavtal |
| **Ramverk** | Python |
| **Bygger från** | EXP-002 |
| **Datum** | 2026-02-19 |

## Mål

Skräddarsydda sökningar definierade med YAML-filer istället för Python-kod.
Användaren beskriver vad som ska hittas i en prompt — Claude utvärderar kandidater
mot den beskrivningen.

Ny sökning = ny YAML-fil (~5 rader). Ingen kod behöver skrivas.

## Problem som löses

EXP-002 kräver Python-kod för varje ny sökstrategi. Det fungerar för utvecklare
men skapar en tröskel för nya söktyper. EXP-003 generaliserar category_classifier.py
till ett prompt-drivet mönster.

## Teknisk design

```
[Prompt-fil (YAML)]
  name: Kvalitetssäkring
  retrieval: heading_semantic
  prompt: "Bedöm om passagen beskriver kvalitetssäkring..."
  threshold: 5
       ↓
[1] Retrieval — använder EXP-002 strategy registry
       ↓
[2] Claude-evaluering — bedömer varje kandidat mot prompten (0-10)
       ↓
[3] Filtrering — score >= threshold
       ↓
[4] Sorterat resultat med motivering
```

## Filstruktur

```
EXP-003_prompt-search/
├── EXPERIMENT.md
├── fixtures/
│   └── success_criteria.yaml
├── learnings.md
├── failures/
├── prompts/                    # Användardefinierade sökprompts
│   ├── kvalitetssäkring.yaml
│   ├── miljökrav.yaml
│   └── säkerhet.yaml
├── src/
│   ├── prompt_engine.py        # Laddar YAML, retrieval + Claude-evaluering
│   └── demo.py                 # CLI
└── requirements.txt
```

## Extensibilitet

Ny sökning:
1. Skapa `prompts/min_sokning.yaml`
2. Kör `python demo.py search min_sokning "sökfråga"`

Klart. Inga kodfiler ändras.
