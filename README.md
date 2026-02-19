# Ramavtal - Semantisk Dokumentsokning v1.0

Semantisk sokning i svenska upphandlingsdokument (PDF/DOCX) med hybrid BM25 + vektorsokning och valfri Claude-klassificering per kategori.

## Arkitektur

```
Dokument (PDF/DOCX)
       |
[1] Parse & chunk (pdfplumber + python-docx)
       |
[2] Embed med KBLab/sentence-bert-swedish-cased (lokal, gratis)
       |
[3] Lagra index (JSON + .npy, hashbaserat)
       |  --- vid sokning ---
[4] Hybrid retrieval: BM25 + Semantic + RRF fusion -> top-k kandidater
       |
[5] (Valfritt) LLM kategori-klassificerare (Claude via Anthropic SDK)
```

## Filstruktur

```
Ramavtal/
  Docs/                      # Dina upphandlingsdokument (PDF/DOCX)
  search.py                  # CLI: indexera, sok, kategori-sok, status
  rag_engine.py              # BM25 + Semantic + Hybrid + RRF + hot-swap
  category_classifier.py     # Claude LLM-klassificering av chunks
  config.py                  # Sokvagar, modellnamn, chunk-parametrar
  requirements.txt           # Dependencies
  .index/                    # Auto-genererad (gitignore:ad)
      manifest.json          # {filnamn: {hash, chunk_range, timestamp}}
      chunks.json            # Alla chunks med metadata
      embeddings.npy         # Embedding-matris (numpy)
```

## Installation

```bash
pip install -r requirements.txt
```

### Krav

- Python 3.10+
- `ANTHROPIC_API_KEY` miljovariabler (krävs enbart for `kategori`-kommandot)

## Anvandning

### Indexera dokument

```bash
python search.py index
```

Forsta korningen bygger ett helt nytt index. Efterfoljande korningar gör inkrementell omindexering — bara nya/andrade filer bearbetas.

Tvinga en fullstandig omindexering:

```bash
python search.py index --force
```

### Visa indexstatus

```bash
python search.py status
```

Visar antal dokument, chunks per fil, och om nagot har andrats sedan senaste indexering.

Exempelutskrift:

```
Indexerade dokument: 10
Totalt antal chunks: 44

  Akademiska_hus_vann.docx: 1 chunks
  Armada_vann_ej.pdf: 5 chunks
  Danderyd_forsta_vann.pdf: 4 chunks
  ...

Index ar uppdaterat.
```

### Fri hybrid-sokning

```bash
python search.py search "timpris"
python search.py search "sakerhetskultur"
python search.py search "miljokrav kemiska produkter"
```

Kombinerar BM25 (nyckelord) med semantisk vektorsokning via Reciprocal Rank Fusion (RRF). Hittar relevanta passager oavsett exakt ordval.

Alternativ:

- `--top-k N` — Antal resultat (default: 10)

### Kategoribaserad sokning (Claude)

```bash
python search.py kategori "Samarbete & kommunikation"
python search.py kategori "Kvalitetsakring"
python search.py kategori "Miljokrav"
```

Pipeline:

1. Hybrid retrieval hamtar 20 kandidater
2. Claude klassificerar varje kandidat mot kategorin (relevans 0-10 + motivering)
3. Filtrerar bort irrelevanta (score < 5)
4. Returnerar sorterat med kalla och motivering

Kraver `ANTHROPIC_API_KEY` och API-kredit.

## Hot-swap: Byt ut dokument

Systemet anvander SHA-256-hashar for att spara vilka dokument som ar indexerade.

1. Lagg till, ta bort eller byt ut filer i `Docs/`
2. Kor `python search.py status` — varnar om andringar
3. Kor `python search.py index` — bara andrade filer omindexeras

Exempel:

```
$ python search.py status
OBS: 2 fil(er) har andrats sedan senaste indexering.
  Nya: Ny_upphandling.pdf
  Borttagna: Gammal_fil.pdf
Kor 'python search.py index' for att uppdatera.

$ python search.py index
Inkrementell omindexering...
  Nya filer: Ny_upphandling.pdf
  Borttagna filer: Gammal_fil.pdf
  Genererade 6 nya chunks.
Index uppdaterat: 46 chunks totalt.
```

## Tekniska detaljer

| Komponent | Val | Motivering |
|---|---|---|
| Embedding-modell | KBLab/sentence-bert-swedish-cased | Bast pa svenska, Pearson 0.93, lokal/gratis |
| Lagring | Flat files (.npy + .json) | 10 dok ~ 44 chunks, behover inte DB |
| BM25 | Ren Python (Okapi BM25, k1=1.5, b=0.75) | Ingen extern dependency |
| Hot-swap | SHA-256 manifest | Inkrementell, snabb, tillforlitlig |
| LLM | Claude Sonnet 4.5 via Anthropic SDK | Kostnadseffektiv for klassificering |
| Chunking | Meningsmedveten, 400 ord/chunk, 50 ord overlap | Bevarar kontext vid meningsgransen |
| Fusion | Reciprocal Rank Fusion (k=60) | Robust kombination av BM25 + semantisk |

## Modulbeskrivningar

### config.py

Centrala konstanter: sokvagar, modellnamn, chunk-storlek. Andras har for att justera systemets beteende.

### rag_engine.py

Karnmodulen med all sokning-logik:

- **Document loading** — `load_pdf()`, `load_docx()`, `load_documents()`
- **Chunking** — `chunk_text()` med meningsmedveten split och overlap
- **SwedishEmbedder** — Wrapper kring `sentence-transformers` for KBLab-modellen
- **BM25** — Okapi BM25 i ren Python
- **rrf_fuse()** — Reciprocal Rank Fusion for att kombinera rankning
- **HybridIndex** — Karnklassen:
  - `build()` — Full indexering
  - `reindex()` — Inkrementell (enbart andrade filer)
  - `search()` — Hybrid BM25 + semantisk + RRF
  - `needs_reindex()` — Kollar om nagot andrats
  - `save()` / `load()` — Persistering till `.index/`

### category_classifier.py

Claude-baserad klassificering:

- `classify_chunks()` — Skickar chunks till Claude for relevansbedomning (0-10 + motivering)
- `search_by_category()` — End-to-end: hybrid retrieval -> Claude-klassificering -> filtrering

### search.py

CLI med fyra kommandon: `index`, `status`, `search`, `kategori`. Auto-detekterar om index ar inaktuellt vid sokning.

## Version

**v1.0** — 2026-02-19
