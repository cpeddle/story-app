# API Docs Skill — Layer 3 Reference

> Companion to `.github/skills/api-docs/SKILL.md`.
> Agents: read this file when you need the full ID table, fallback URLs, or annotation/failure logs.

---

## Design Decision Log

| ID | Date | Decision | Alternatives Rejected | Rationale |
|---|---|---|---|---|
| D-1 | 2026-04-17 | **Option A — chub-primary with fallback URL list** | Option B (static snapshot): stale maintenance burden. Option C (always fetch_webpage): no persistence, no curation. | All 8 Python tooling deps confirmed in chub CDN catalog. Android/Kotlin gap handled by fallback URL table. chub annotations provide cross-session learning that Options B/C cannot match. |

**Known chub CLI limitation (v0.1.3, Windows):** `chub search <query>` only searches the 20-entry bundled local registry — not the full CDN catalog. Always use `chub get <id>` directly from the Confirmed ID table below. A Windows path separator bug (`lastIndexOf('/')` on backslash paths) is patched locally in `cache.js`; fix is upstream in PR #144, awaiting next npm release.

---

## Chub Catalog — Confirmed IDs

Use these IDs directly with `chub get <id> --lang py`. Verified 2026-04-17.

| Dependency | chub ID | Notes |
|---|---|---|
| Anthropic Python SDK | `anthropic/claude-api` | Claude API: chat, streaming, tool use, vision, batch |
| Google Gemini Python SDK | `gemini/genai` | `google-genai` package (not `google.generativeai`) |
| OpenAI Python SDK | `openai/chat` | Chat completions, streaming, function calling, vision, embeddings |
| Mistral AI Python SDK | `mistralai/package` | Chat completions, embeddings, files, OCR |
| jsonschema (Python) | `jsonschema/package` | JSON Schema validation, format checks |
| pytest (Python) | `pytest/package` | Setup, fixtures, parametrization, plugins |
| CairoSVG (Python) | `cairosvg/package` | SVG → PNG/PDF/PS conversion |
| Pillow (Python) | `pillow/package` | Image processing, format handling |

---

## Fallback URL Catalogue

For dependencies NOT in the chub catalog, use `fetch_webpage` with these URLs.

| Dependency | URL | Format | Quality | Verified |
|---|---|---|---|---|
| Jetpack Compose | https://developer.android.com/jetpack/compose/documentation | Tutorial index + API ref | ✅ Excellent — Kotlin, updated 2026-03 | 2026-04-17 |
| Hilt (Android DI) | https://developer.android.com/training/dependency-injection/hilt-android | Full guide | ✅ Excellent — Kotlin code samples, updated 2026-03 | 2026-04-17 |
| Room (Android persistence) | https://developer.android.com/training/data-storage/room | Full guide | ✅ Excellent — Kotlin code samples, updated 2026-03 | 2026-04-17 |
| Kotlin DSL / Gradle | https://docs.gradle.org/current/userguide/kotlin_dsl.html | Reference | ✅ Good — official Gradle docs | 2026-04-17 |
| Kotlin coroutines | https://kotlinlang.org/docs/coroutines-guide.html | Tutorial + reference | ✅ Good — official Kotlin docs | 2026-04-17 |
| Kotlinx Serialization | https://github.com/Kotlin/kotlinx.serialization/blob/master/docs/serialization-guide.md | Markdown guide | ✅ Good — navigable, GitHub-hosted | 2026-04-17 |
| Jetpack Navigation (Compose) | https://developer.android.com/jetpack/compose/navigation | Guide | ✅ Good — Compose-specific, Kotlin | 2026-04-17 |
| SoundPool (Android audio) | https://developer.android.com/reference/android/media/SoundPool | API reference | ✅ Terse but complete Java/Kotlin API ref | 2026-04-17 |
| DataStore (Android prefs) | https://developer.android.com/topic/libraries/architecture/datastore | Guide | ✅ Good — updated 2026 | 2026-04-17 |
| Recraft API | https://www.recraft.ai/docs | REST API docs | ✅ Good — accessible without auth | 2026-04-17 |
| Gemini REST API | https://ai.google.dev/gemini-api/docs | REST + SDK docs | ✅ Good — Python SDK and REST endpoints | 2026-04-17 |
| Nano Banana API | https://docs.nananobanana.com/en/api | REST API docs | ⚠️ Pending — verify during I-1 investigation | 2026-04-17 |

---

## Project-Specific Annotation Log

Mirror of all `chub annotate` calls made during project sessions. Future agents: add a row here whenever you run `chub annotate`.

| Package ID | Annotation | Added |
|---|---|---|
| `anthropic/claude-api` | Streaming responses: iterate `.text_stream` attribute — `.content` is not populated until stream is fully consumed | 2026-04-17 |
| `gemini/genai` | Use `google-genai` package (not legacy `google.generativeai`); current model names: `gemini-2.5-pro`, `gemini-2.0-flash`; `PIL.Image` required for vision input, not raw bytes | 2026-04-17 |
| `cairosvg/package` | SVG input must be valid XML; use `cairosvg.svg2png(url=path)` not `bytestring=` for file-based inputs; invalid SVG silently produces empty output | 2026-04-17 |
| `pillow/package` | `PIL.Image.open(f).verify()` raises on invalid format but also closes the file handle — reopen the file after verify before any further processing | 2026-04-17 |

### Annotation Ledger Instructions

1. Run `chub annotate <id> "<note>"` after discovering a gotcha, workaround, or version quirk.
2. Add the annotation as a new row in the table above immediately.
3. Keep notes concise and actionable — do not repeat what is already in the upstream doc.
4. At compound-engineering step time, the detection checklist will prompt a sweep for new annotations in the session.

---

## Skill Failure Log

Record here every session in which the `api-docs` skill failed or produced unusable results.
This log feeds into the compound-engineering structural gap process.

**Failure modes:** `no-chub-id` | `bad-fallback-url` | `empty-content` | `stale-doc` | `auth-required`
**Resolutions:** `fallback-url-added` | `annotation-added` | `chub-pr-raised` | `pending`

| Date | API / Package | Failure Mode | Workaround Used | Resolution |
|---|---|---|---|---|
| 2026-04-17 | `pillow/package`, `cairosvg/package`, `jsonschema/package`, `mistralai/package`, `pytest/package` | Windows `mkdir ''` path separator bug in chub v0.1.3 | Patched `cache.js` `lastIndexOf('/')` → `dirname()` | Full fix in upstream PR #144; local patch applied. Will be resolved in next npm release. |

---

## Compound Engineering Integration Notes

The compound-engineering detection checklist (added during this exec plan) includes two rows
that trigger automatically when working with this skill:

| Signal | Action |
|---|---|
| `chub annotate` called in session | Mirror annotation to Annotation Log above |
| `api-docs` skill returned no/unusable result | Log to Skill Failure Log; invoke compound-engineering to propose structural fix |

At session end (compound step), review both logs for new entries added during the session.
