---
name: art-pipeline
description: 'Flat vector / SVG art style specification, paper-doll layer stacks, asset generation pipeline, quality gates, and runtime recolouring rules for Story App. Invoke when generating art assets, defining SVG structure, implementing the rendering pipeline, or evaluating asset quality.'
---

# Art Pipeline — Story App

## When to Use This Skill

Invoke when:
- Generating or evaluating character sprites, scene backgrounds, or object art
- Defining SVG structure for paper-doll parts
- Implementing or modifying the rendering/compositing pipeline
- Setting up asset quality gates
- Working with runtime recolouring
- Organising the asset archive

## Style Specification (TD-15, TD-17)

### Visual Identity

- **Style:** Flat vector — geometric composition, bold outlines, flat colour fills
- **Proportions:** Chibi / kawaii — large head, small body, expressive features
- **Rendering:** Scale-agnostic vectors (SVG-first, PNG fallback acceptable)
- **Target:** Friendly, approachable, kid-safe aesthetic for a 7-year-old
- **Uniformity (TD-17):** Characters and scenes share the same unified flat vector style — no mixed-style approach
- **Canonical style reference:** Outdoor-carriage scene (`assets/style-reference/canonical-style.jpg`)

### Style Rules

- Flat colour fills only — no gradients, no textures, no painterly effects
- Bold consistent outlines — uniform stroke width across all assets
- Geometric simplification — reduce complex shapes to basic forms
- Limited colour palette per character
- No photorealistic elements, no 3D shading, no perspective depth

### Known Style Issues (Archive Audit)

| Asset | Status | Issue |
|-------|--------|-------|
| Outdoor carriage | PASS | Matches flat vector spec — **canonical style reference** |
| Castle corridor | PASS — REGENERATED | N-7 (2026-04-16): `recraft-corridor-v1.svg` passes full spec. Archive versions all failed. |
| Throne room | PASS — REGENERATED | N-7 (2026-04-16): `recraft-throne-room-v1.svg` passes full spec. All archive versions failed. |

Use passing assets as style reference. Failing assets must be regenerated.  
**N-4 compositing test (2026-04-16): ✅ COMPATIBLE** — princess-full-v5 + carriage-scene-v4 composite passes; style match STRONG, colour COMPLEMENTARY.  
**Canonical style file:** `assets/style-reference/canonical-style.jpg` (N-6 complete).

## Generation Tooling Summary

Current adopted tools per asset type:

| Asset type | Tool | Format | Limitation | Investigation |
|---|---|---|---|---|
| Scene backgrounds (landscape) | Gemini (manual, AD-9) | Raster PNG, landscape | No scripting; no style-anchor input | ⬜ RS-7 evaluating Nano Banana API as replacement |
| Character sprites (square) | Recraft v3 `vector_illustration` (AD-5/AD-8) | SVG (rasterised to PNG for app) | Square 1024×1024 only; text-only | ⬜ RS-7 evaluating Nano Banana API as supplement |
| Object sprites | Gemini (manual, AD-9) + `n8_bg_remove.py` | Transparent PNG | Same as scene backgrounds | — |

**Nano Banana API (RS-7 — in progress):** Unified REST API (`POST /api/v1/generate`) wrapping
Gemini 2.5 Flash Image (default) + Pro models. Supports `referenceImageUrls` for image-to-image
style anchoring and `aspectRatio` for landscape output. If confirmed viable, would replace the
manual Gemini workflow (AD-9) and add style anchoring to sprite generation.
See [`references.md`](references.md) § Nano Banana API and
[`RS-7_NanoBananaEvaluation.md`](../../docs/investigations/RS-7_NanoBananaEvaluation.md).

## Paper-Doll Layer Stacks

Three archetypes — **Humanoid** (Knight, Princess), **Creature** (Dragon) — each with defined Z-order layers, parts, and colour slots. Total budget: 53 / 100 parts. See [`references.md`](references.md) for layer stack tables and part inventory.

## Rendering Pipeline (TD-16)

### Split Body/Face Architecture

Characters use **Option B: split body/face caches** for dynamic mood expressions.

1. Load SVG parts from assets
2. Compose **body** layers (body-base + outfit + hair + accessories) by Z-order
3. Compose **face** layers (eyes + mouth + nose) separately — one per mood state
4. Apply CSS fill overrides for recolouring
5. Rasterise body and face to separate `ImageBitmap`s on `Dispatchers.IO`
6. Cache body bitmap (invalidate on paper-doll change)
7. Cache face bitmaps per mood variant (happy/neutral/grumpy — 3 per character)
8. Draw via `Canvas.drawImage()` — 2 drawBitmap calls per character (body + current face)

Key: body rasterisation ~75ms, face rasterisation ~30ms. Face swaps are instant (bitmap lookup).
Total cache: ~57.6 MB for 6 characters × 4 bitmaps each (1 body + 3 faces).

## Quality Gates

Character parts, scene backgrounds, and batch-level quality checks. All criteria documented in [`references.md`](references.md), including checklists and failure criteria (40% batch failure → full regeneration).

## Deep Reference

See [`references.md`](references.md) for layer stack tables, SVG authoring rules, quality gate checklists,
asset generation workflow (Recraft + Gemini + Nano Banana), prompt-log requirement, recolouring details,
and open questions.

See [`RS-7_NanoBananaEvaluation.md`](../../docs/investigations/RS-7_NanoBananaEvaluation.md) for the
full Nano Banana investigation (model catalogue, API capabilities, scene and sprite quality test findings).
