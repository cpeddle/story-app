---
name: api-docs
description: "Fetch current API documentation before writing code against any third-party library, SDK, or external REST API. Invoke when using anthropic, openai, google-genai, mistralai, pillow, cairosvg, jsonschema, pytest, Recraft, Gemini, Nano Banana, or any unfamiliar library. Covers chub CLI retrieval, Android/Kotlin fallback URLs, annotation persistence, and failure tracking."
---

# API Docs Retrieval — Story App

## When to Use This Skill

**Invoke BEFORE writing any code** that calls a third-party library or external REST API. Specifically:
- Writing code against any Python package (LLM SDKs, image processing, validation, testing)
- Calling any external REST API (Recraft, Gemini, Nano Banana)
- Implementing any Android/Kotlin framework API (Compose, Hilt, Room, DataStore, coroutines)
- Asked about method signatures, parameter names, or version-specific behaviour
- Unsure whether an API shape is current or based on training knowledge

## Primary Path — chub CLI

Use `chub get` directly by ID (do NOT use `chub search <query>` — search only covers the 20-entry bundled local catalog, not the full CDN). See the confirmed ID table in [`references.md`](references.md).

```
# Step 1 — Fetch by confirmed ID
chub get anthropic/claude-api --lang py

# Step 2 — Use the docs
# Read content, write accurate code from what the docs say.

# Step 3 — Annotate what you learned (project-specific gotchas)
chub annotate anthropic/claude-api "streaming requires .text_stream not .content"
# ALSO mirror to references.md Annotation Log (see Annotation Convention below)

# Step 4 — Rate the doc
chub feedback anthropic/claude-api up --label accurate "Models list is current"
```

## Fallback Path — fetch_webpage

Use `fetch_webpage` when the dependency has no chub ID. Check [`references.md`](references.md) for the confirmed fallback URL table covering all Android/Kotlin framework APIs and project-specific REST APIs.

Decision logic:
```
Is there a confirmed chub ID in references.md?
  YES → chub get <id> --lang py
  NO  → fetch_webpage with the URL from references.md Fallback URL Catalogue
  Not listed at all → chub get <id> --lang py (try reasonable guess), if fails:
                      find official docs URL, add to references.md fallback table
```

## Annotation Convention

After discovering a project-specific gotcha, workaround, or version quirk:

1. Run: `chub annotate <id> "<concise note>"`
2. **Also** add a row to the Annotation Log in [`references.md`](references.md):

```
| anthropic/claude-api | streaming requires .text_stream not .content | 2026-04-17 |
```

Annotations persist locally and appear on the next `chub get`. Mirror ensures portability.

## Failure Tracking

When retrieval fails or returns unusable content (empty doc, wrong library, stale API):

1. **Do NOT proceed with guessed or hallucinated API shapes.**
2. Log the failure in the **Skill Failure Log** in [`references.md`](references.md):
   - Package/API name, failure mode (`no-chub-id` / `bad-fallback-url` / `empty-content` / `stale-doc`), workaround used, date
3. Invoke the **`compound-engineering`** skill to classify the failure as a structural gap and propose one of:
   - Add fallback URL to `references.md` (if uncovered API)
   - Promote workaround to seed annotation (if recurring)
   - Raise chub upstream PR (if general gap)

## Quick Reference

| Command | Purpose |
|---|---|
| `chub get <id> --lang py` | Fetch Python docs by confirmed ID |
| `chub get <id> --full` | Fetch all reference files for a doc |
| `chub get <id> --lang py -o doc.md` | Save to file |
| `chub annotate <id> "<note>"` | Add a persistent local note |
| `chub annotate --list` | List all annotations |
| `chub feedback <id> up --label accurate "<reason>"` | Rate doc positively |
| `chub feedback <id> down --label outdated "<reason>"` | Flag stale content |

Feedback labels: `outdated` `inaccurate` `incomplete` `wrong-examples` `wrong-version` `poorly-structured` `accurate` `well-structured` `helpful` `good-examples`

> Full ID table, fallback URLs, annotation log, and failure log → [`references.md`](references.md)
