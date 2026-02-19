# Mall: Hur du beskriver ett experiment

---

## PROMPT - Kopiera och anpassa

```markdown
# Experiment: [NAMN]

## Target Repo
https://github.com/Sytematic1036/[REPO-NAMN]

INNAN du skriver kod:
1. Undersök repot via GitHub API (gh api eller WebFetch)
2. Identifiera ramverk (FastAPI? Flask? React? Next.js?)
3. Studera hur liknande funktioner är implementerade
4. Notera patterns och kodstil

Du MÅSTE använda samma arkitektur och ramverk som repot.
Skriv ENDAST ny kod - kopiera ALDRIG befintlig kod.

## Bygger från
[EXP-XXX eller "-" om nytt]

## Mål
[1-2 meningar: Vad ska uppnås]

## Framgångskriterier

### Prototyp (kan testas isolerat)
1. [ ] [Kriterium] → Test: `[kommando]`
2. [ ] [Kriterium] → Test: `[kommando]`

### Integration (testas mot target repo)
3. [ ] Koden följer samma patterns som target repo
4. [ ] Koden kan kopieras till target repo utan ändringar
5. [ ] Alla tester passerar efter kopiering

### Edge cases
1. [ ] [Kantfall 1] → [Förväntat beteende]
2. [ ] [Kantfall 2] → [Förväntat beteende]

## Begränsningar
- [Vad får INTE göras]
- [Max dependencies]
- [Andra restriktioner]
```

---

## MINIMAL PROMPT - För enkla experiment

```markdown
# Experiment: [NAMN]

## Target Repo
https://github.com/Sytematic1036/[REPO]
Undersök repot först. Använd samma arkitektur. Skriv endast ny kod.

## Mål
[En mening]

## Framgångskriterier
1. [ ] [Kriterium 1]
2. [ ] [Kriterium 2]
3. [ ] Fungerar när kopierad till target repo

## Edge cases
1. [ ] [Kantfall]
```

---

## Checklista

- [ ] Target Repo med GitHub-URL
- [ ] Instruktion att undersöka repot FÖRST
- [ ] "Samma arkitektur" nämnt
- [ ] "Endast ny kod" nämnt
- [ ] Minst 2 prototyp-kriterier
- [ ] Minst 1 integration-kriterium
- [ ] Minst 1 edge case
