# Ramavtal Experiments

Centralt experiment-system. Alla experiment sparas här och hänvisar till sitt Target Repo.

## Aktiva experiment

| ID | Namn | Target Repo | Status | Bygger från |
|----|------|-------------|--------|-------------|
| - | - | - | - | - |

## Flöde

```
1. Beskriv experiment med Target Repo
         ↓
2. Claude undersöker target repo via GitHub API
   (inget behov att klona)
         ↓
3. Claude skriver ENDAST ny kod till experiments/
   (följer target repos arkitektur)
         ↓
4. Testa integration manuellt eller automatiskt
         ↓
5. När VERIFIED → PR till target repo
```

## Struktur per experiment

```
experiments/EXP-XXX_namn/
├── EXPERIMENT.md              # Status, target repo, mål
├── fixtures/
│   └── success_criteria.yaml  # Vad = framgång
├── learnings.md               # Vad fungerade + INTE
├── failures/                  # Misslyckade approaches
├── iterations/                # Versionshistorik
│   └── v1_initial/
│       ├── src/               # Kod för denna iteration
│       ├── notes.md           # Dokumentation
│       └── timestamp.txt      # YYYY-MM-DD_HHMM
├── src/                       # AKTUELL version (ny kod)
└── integration_test.sh        # Valfritt: custom testskript
```

## Regler

1. **ENDAST ny kod** i experiments - kopiera ALDRIG från target repo
2. **Samma arkitektur** som target repo (undersök först!)
3. **RADERA ALDRIG failures/** - förhindrar upprepade misstag
4. **Target Repo** är ALLTID en GitHub-URL
5. **Varje iteration** sparas i iterations/ med timestamp

## Status-definitioner

| Status | Betydelse |
|--------|-----------|
| `EXPERIMENTAL` | Pågående, ej testat mot target repo |
| `VERIFIED` | Integration-test passerar |
| `FAILED` | Misslyckades (dokumenterat varför) |
| `PROMOTED` | Mergat till target repo via PR |
