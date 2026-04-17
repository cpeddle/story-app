# RS-3 Art Pipeline — Prompt Log

Mandatory log per AD-3. Every generation session appends an entry here.  
Format: tool used, exact prompt, style reference, settings, selected variant, notes.

---

## Phase 1 Archive Assets (DALL-E 3 via ChatGPT — prompts not preserved)

All assets in `assets/archive/` were generated prior to AD-3 (prompt preservation mandate).
Prompts are unknown. This is documented as F-6 in RS-3 Phase 1 findings.

---

## Phase 2 — N-4 Composite Test — 2026-04-16

**Task:** N-4 — Background removal and compositing test  
**Tool:** Python (Pillow 12.2.0 + numpy + scipy.ndimage) — no AI generation in this step  
**Input:** `assets/archive/characters/princess/princess-full-v5.jpg`  
**Processing:**
- Background removal: numpy RGB threshold `R≥240, G≥236, B≥230` + 2px `binary_dilation`
- Composite: princess at 22% scene height (294px) on carriage-scene-v4 at 2000×1340
**Outputs:**
- `assets/archive/characters/princess/princess-full-v5.png` — transparent PNG, clean edges
- `assets/archive/characters/princess/n4-composite-test.jpg` — composite preview
**Outcome:** ✅ COMPATIBLE — background removal clean, style match confirmed (see RS-3 §12.1)

---

## Phase 2 — N-5 Recraft v3 Evaluation — 2026-04-16

**Task:** Generate princess-full in Recraft v3 flat vector style, compare to archive princess-full-v5  
**Script:** `tools/rs3/n5_recraft_eval.py`

| Field | Value |
|---|---|
| **Tool** | Recraft v3 REST API (`external.api.recraft.ai/v1/images/generations`) |
| **Prompt** | `chibi kawaii princess character, full body, flat geometric shapes, bold black outline, pink ballgown dress, golden crown, brown hair, large round eyes, simple flat colour fills, white background, no gradients, no shadows, no textures, vector illustration style` |
| **Styles evaluated** | `vector_illustration` (2 variants), `icon` (2 variants), `digital_illustration` (2 variants) |
| **Size** | 1024×1024 |
| **Selected styles** | `vector_illustration` v1 and v2 (see AD-7) |
| **Output directory** | `assets/archive/characters/princess/recraft/` |
| **Output formats** | `vector_illustration` → SVG (with PNG render); `icon` → SVG (gradients present); `digital_illustration` → WebP |
| **Notes** | Recraft returns SVG for vector/icon styles — files were initially saved with `.png` extension causing a vision analysis failure loop in the previous session agent. Corrected to `.svg`/`.webp` with cairosvg-rendered PNG previews alongside. |

**Outcome:** ✅ `vector_illustration` RECOMMENDED — flat fills, bold black outlines, no gradients, no shadows, TD-15/TD-17 compliant. SVG format preferred over DALL-E 3 raster for RS-4 paper doll system. See RS-3 §12.3.

---

## Phase 2 — N-7 Scene Regeneration — 2026-04-16

**Task:** N-7 — Regenerate throne room + corridor in flat vector kawaii style (Recraft v3)
**Tool:** Recraft v3 REST API, style=`vector_illustration`, size=`1024x1024`
**Style anchor:** Carriage-scene-v4 style characteristics encoded in text prompt (Recraft is text-only, no image-ref parameter)
**Size constraint (AD-8):** Recraft V4 Vector supports 1024×1024 only. SVG scales losslessly to 2000×1340 at runtime.

### Throne Room Prompt
```
castle throne room interior scene, flat vector kawaii illustration, low-poly geometric shapes, bold black outlines, flat solid colour fills, golden throne on raised stone dais centered in composition, simplified flat arched stone walls, tall arched window in back wall with flat sky visible, flat geometric stone tile floor, warm gold amber and stone grey colour palette, open archway on left wall and open archway on right wall as natural exit zones, wall-mounted torch brackets as simple flat shapes, no gradients, no shadows, no ambient occlusion, no directional lighting effects, no stone texture detail, no stone masonry grout, no glow, no bloom, fairy tale game background art, flat 2D game scene
```

### Corridor Prompt
```
castle stone corridor interior scene, flat vector kawaii illustration, low-poly geometric shapes, bold black outlines, flat solid colour fills, straight corridor with flat arched vaulted ceiling, stone block walls as flat rectangular colour panels, simple torch bracket shapes on walls with flat orange flame, flat geometric stone tile floor path leading to arched exit, warm grey amber and gold colour palette, open archway exit visible at straight-ahead far end of corridor, no gradients, no shadows, no directional lighting, no atmospheric bloom or glow, no stone texture or masonry grout detail, no ambient occlusion, no fog or haze, fairy tale game background art, flat 2D game scene
```

### Results
- `recraft-throne-room-v1.png`: ok [svg] 144KB
- `recraft-throne-room-v2.png`: ok [svg] 218KB
- `recraft-corridor-v1.png`: ok [svg] 210KB
- `recraft-corridor-v2.png`: ok [svg] 165KB

---

## Phase 2 — N-12 Gemini Landscape Scene Test — 2026-04-16

**Task:** N-12 — Generate landscape scene backgrounds via Gemini (AD-9). Manual paste into Gemini UI.
**Tool:** Gemini image generation (manual), 16:9 landscape PNG output
**Source prompts:** `tools/rs3/gemini-scene-prompts.md`
**Output folder:** `assets/RS-3 Gemini Test/`

### Results

| Scene | File | Style | Exits | Verdict |
|---|---|---|---|---|
| outdoor-carriage | `outdoor-carriage.png` | ✅ PASS | ✅ Both gaps present | ✅ ACCEPT |
| castle-throne-room | `castle-throne-room.png` | ⚠️ minor ceiling gradient | ✅ Both arches present | ✅ ACCEPT |
| castle-corridor | `castle-corridor.png` (pass 2) | ✅ PASS | ✅ All 3 exits present | ✅ ACCEPT |

**Pass 1 images archived to:** `assets/RS-3 Gemini Test/pass1/`

### Pass 2 — Corridor retry (updated prompt)

**Changes from pass 1:** Added explicit `IMPORTANT` paragraph — NO floor-edge darkening, NO AO fringe, NO bloom/glow on far-end arch, flat solid fill on every surface. All three pass 1 failures resolved.

### Measured Exit Positions (normalised, from accepted images)

**outdoor-carriage:**
| Exit | x | y |
|---|---|---|
| Left gap (castle gate) | ~0.08 | ~0.76 |
| Right gap (garden path) | ~0.91 | ~0.76 |

**castle-throne-room:**
| Exit | x | y |
|---|---|---|
| Left arch (corridor) | ~0.10 | ~0.62 |
| Right arch (second wing) | ~0.89 | ~0.62 |

**castle-corridor (pass 2 — accepted):**
| Exit | x | y |
|---|---|---|
| Left door (bedroom A) | 0.13 | 0.66 |
| Right door (bedroom B) | 0.87 | 0.66 |
| Far end archway | 0.50 | 0.52 |

### Corridor Retry Note
Corridor prompt updated in `gemini-scene-prompts.md` v2: added explicit NO floor-edge darkening, NO perspective-fade gradients, flat far-end archway colour (peach/sky blue with bold black outline). Retry corridor and replace file if accepted.

## Phase 2 — N-8 Background Removal Batch — 2026-04-17

**Task:** N-8 — Background removal pass on selected character sprites
**Tool:** Python (numpy + scipy.ndimage flood fill, 2px dilation) — `tools/rs3/n8_bg_remove.py`
**Technique:** Edge-connected flood fill from image border through pixels within Euclidean RGB
distance of sampled background colour; 2px dilation to erase anti-aliasing fringe.

| Sprite | Output | BG Colour | FG % | Verdict |
|---|---|---|---|---|
| `knight-full-v4.jpg` | `assets\archive\characters\knight\knight-full-v4.png` | R=250 G=249 B=247 | 27.7% | ✅ OK |
| `dragon-full-v4.jpg` | `assets\archive\characters\dragon\dragon-full-v4.png` | R=246 G=216 B=178 | 55.2% | ✅ OK |
| `dragon-full-v2.jpg` | `assets\archive\characters\dragon\dragon-full-v2.png` | R=38 G=33 B=46 | 47.8% | ✅ OK |

## Phase 2 — N-9 Part Anchor System Test — 2026-04-17

**Task:** N-9 — Test whether archive princess parts composite correctly onto full-body sprite
**Tool:** Python (Pillow + numpy + scipy.ndimage flood fill) — `tools/rs3/n9_part_anchor.py`
**Parts tested:** `princess-crown-v4.jpg`, `princess-hair-long-v4.jpg`, `princess-outfit-ballgown-blue-v4.jpg`
**Base:** `princess-full-v5.png` (1024×1024 transparent)

| Part | BG Colour | FG % | Bounding Box | Crown Row Position |
|---|---|---|---|---|
| `princess-crown-v4.jpg` | R=249 G=252 B=245 | 10.8% | rows 0.29–0.75h, cols 0.18–0.82w | Mid-canvas (should be top of head) |
| `princess-hair-long-v4.jpg` | R=253 G=254 B=253 | 41.5% | rows 0.07–0.93h, cols 0.10–0.90w | Full canvas height |
| `princess-outfit-ballgown-blue-v4.jpg` | R=251 G=245 B=233 | 32.7% | rows 0.11–0.90h, cols 0.14–0.91w | Full canvas height |

**Outcome:** ❌ MISALIGN — all three parts are misaligned against full-body sprite at 1:1 scale.
Parts were generated as isolated hero images filling most of the canvas, with no shared positional anchor.
**Conclusion:** Archive parts are NOT reusable for paperdoll compositing. RS-4 must use inpainting or full-combination generation. See RS-3 §12.7.

**Output images:** `assets/archive/characters/princess/n9-part-composite-test.png`, `n9-parts-bgremoved/`

## Phase 2 — N-11 Text Descriptions for Finalized Scenes — 2026-04-17

**Task:** N-11 — Write companion text descriptions for all 3 accepted MVP scene backgrounds (AD-5, REC-8)
**Tool:** Manual authoring based on visual review of accepted Gemini PNG files
**Reference images:** `assets/RS-3 Gemini Test/` (pass 2 corridor, pass1/ outdoor-carriage + throne-room)

| Scene | File | Action |
|---|---|---|
| outdoor-carriage | `tools/rs5/text-descriptions/outdoor-carriage.txt` | Updated — Gemini image described; flat style keywords; cleaner exit language |
| castle-throne-room | `tools/rs5/text-descriptions/castle-throne-room.txt` | Created — new file describing throne dais, symmetrical arch exits, stained glass, banners |
| castle-corridor | `tools/rs5/text-descriptions/castle-corridor.txt` | Updated — rounded arches, no bedroom reference, no AO note, far archway as far-end exit |

**Outcome:** ✅ DONE — 3 text description files ready for RS-5 template generation pipeline.


