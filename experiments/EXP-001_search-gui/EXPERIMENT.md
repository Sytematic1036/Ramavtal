# EXP-001: Sök-GUI för Ramavtal

| Fält | Värde |
|------|-------|
| **Status** | EXPERIMENTAL |
| **Target Repo** | https://github.com/Sytematic1036/Ramavtal |
| **Ramverk** | Python / FastAPI |
| **Bygger från** | - |
| **Datum** | 2026-02-19 |

## Mål

Skapa ett webbgränssnitt (GUI) för att söka i upphandlingsdokument i Docs/-mappen.
Stödjer både fri hybrid-sökning (BM25 + semantisk) och kategori-sökning (Claude-klassificering).

## Teknisk design

```
┌─────────────────────────────────────────────────────────────┐
│ Browser - http://localhost:8000                              │
│                                                              │
│  [Sökfält.................................] [Sök]            │
│                                                              │
│  ( ) Fri sökning    ( ) Kategorisökning                      │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ Resultat 1 — Källa: fil.pdf (score: 0.82)             │  │
│  │ "Textutdrag från dokumentet..."                        │  │
│  ├────────────────────────────────────────────────────────┤  │
│  │ Resultat 2 — Källa: fil2.docx (score: 0.71)           │  │
│  │ "Textutdrag från dokumentet..."                        │  │
│  └────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼ POST /api/search eller /api/kategori
┌─────────────────────────────────────────────────────────────┐
│ Backend (FastAPI)                                            │
│  • Laddar HybridIndex från .index/                           │
│  • Fri sökning: index.search(query)                          │
│  • Kategorisökning: search_by_category(category, index)      │
└─────────────────────────────────────────────────────────────┘
```

## Filstruktur

```
EXP-001_search-gui/
├── EXPERIMENT.md
├── fixtures/
│   └── success_criteria.yaml
├── learnings.md
├── failures/
├── src/
│   ├── app.py              # FastAPI backend
│   └── templates/
│       └── index.html      # GUI
└── requirements.txt
```

## Nästa steg

- [ ] Testa med indexerade dokument
- [ ] Verifiera kategori-sökning med API-nyckel
- [ ] Eventuellt: lägga till filtrering per dokument
