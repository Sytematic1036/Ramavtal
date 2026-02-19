# EXP-002: Rubrik-medveten sökning (Heading Search)

| Fält | Värde |
|------|-------|
| **Status** | EXPERIMENTAL |
| **Target Repo** | https://github.com/Sytematic1036/Ramavtal |
| **Ramverk** | Python |
| **Bygger från** | - |
| **Datum** | 2026-02-19 |

## Mål

1. Bevara dokumentstruktur (rubriker, sektioner) vid indexering
2. Skapa en extensibel Strategy Registry för skräddarsydda sökningar
3. Första strategin: "heading" — hitta stycken under rubriker som matchar nyckelord

## Problem som löses

Nuvarande pipeline tappar all dokumentstruktur:
- `load_docx()` kastar bort heading-styles
- `load_pdf()` kastar bort fontstorlek
- `chunk_text()` delar utan hänsyn till sektionsgränser
- Chunks saknar heading-metadata → strukturerad sökning omöjlig

## Teknisk design

```
[Indexering — nytt]
load_docx_structured() → paragraphs med {text, heading, section_path, element_type}
load_pdf_structured()  → paragraphs med {text, heading, section_path, element_type}
        ↓
chunk_text_structured() → chunks som ärver heading-metadata
        ↓
EnrichedIndex.build() → chunks.json med heading-fält + embeddings.npy

[Sökning — nytt]
search_strategies.py
  @register_strategy("hybrid")   → Befintlig BM25+semantisk
  @register_strategy("heading")  → Chunks vars rubrik matchar nyckelord
  @register_strategy("heading_semantic") → Semantisk heading-match → alla stycken under
  ... fler strategier läggs till med en decorator
```

## Filstruktur

```
EXP-002_heading-search/
├── EXPERIMENT.md
├── fixtures/
│   └── success_criteria.yaml
├── learnings.md
├── failures/
├── src/
│   ├── structured_loader.py    # Heading-aware DOCX/PDF loading
│   ├── search_strategies.py    # Strategy registry + strategier
│   ├── enhanced_index.py       # Utökar HybridIndex med metadata
│   └── demo.py                 # Test/demo-skript
└── requirements.txt
```

## Extensibilitet

Ny strategi = en funktion:
```python
@register_strategy("min_nya_sokning")
def strategy_custom(query, index, **kwargs):
    # filtrera, ranka, returnera
    return results
```
Inga andra filer behöver ändras.
