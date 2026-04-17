# Art Pipeline — References

Companion document to [`SKILL.md`](SKILL.md). Contains complete layer stacks, SVG authoring spec, generation workflow, quality gate checklists, and open questions.

**Key decisions:** TD-15 (flat vector style), TD-16 (hybrid SVG rendering with split body/face caches), TD-17 (unified flat vector style for characters and scenes).

## Paper-Doll Layer Stacks — Full Specification

### Humanoid Archetype (Knight, Princess)

Z-order bottom to top:

| Layer | Z | Parts | Slots |
|-------|---|-------|-------|
| Body | 0 | body-base | skin tone |
| Outfit | 1 | outfit-top, outfit-bottom | primary, secondary colours |
| Face | 2 | eyes, mouth, nose | expression set |
| Hair | 3 | hair-style | colour |
| Accessory | 4 | hat, crown, helmet, etc. | optional |

**Knight parts (17):** body-base, outfit-tunic, outfit-pants, outfit-boots, outfit-gloves, face-eyes (x3 expressions), face-mouth (x3), face-nose, hair (x3 styles), accessory-helmet, accessory-sword

**Princess parts (19):** body-base, outfit-dress, outfit-tiara-dress, outfit-shoes, face-eyes (x3), face-mouth (x3), face-nose, hair (x4 styles), accessory-crown, accessory-wand, accessory-necklace

### Creature Archetype (Dragon)

Z-order bottom to top:

| Layer | Z | Parts | Slots |
|-------|---|-------|-------|
| Body | 0 | body-base | primary colour |
| Wings | 1 | wing-left, wing-right | membrane colour |
| Tail | 2 | tail | matches body |
| Horns | 3 | horns | accent colour |
| Face | 4 | eyes, mouth | expression set |
| Accessory | 5 | collar, hat, etc. | optional |

**Dragon parts (17):** body-base, wing-left, wing-right, tail, horns, face-eyes (x3), face-mouth (x3), face-nose, accessory-collar, accessory-hat, accessory-scarf
### Mood-Driven Face Layers (TD-16)

Face layers are composed and cached **separately** from body layers to support dynamic mood expressions without re-rasterising the entire character.

Each archetype has 3 face mood variants (pre-rasterised at character creation/edit time):

| Mood | Eyes | Mouth | Notes |
|------|------|-------|-------|
| Happy | face-eyes-happy | face-mouth-happy | MoodEngine state: FRIENDLY |
| Neutral | face-eyes-neutral | face-mouth-neutral | MoodEngine state: NEUTRAL |
| Grumpy | face-eyes-grumpy | face-mouth-grumpy | MoodEngine state: GRUMPY |

Face composition: combine eyes + mouth + nose SVGs into a single face `ImageBitmap` per mood. Nose is shared across all moods.

**Rendering at play time:** `Canvas.drawImage(bodyBitmap)` then `Canvas.drawImage(faceBitmaps[currentMood])` — 2 draw calls per character. Face swap is instant (bitmap lookup, no rasterisation).

**Cache budget:** 6 characters × (1 body + 3 faces) = 24 bitmaps × ~2.4 MB each = **~57.6 MB total**.
### Combinatorial Budget

- Total SVG parts: 53 (17 + 19 + 17)
- Budget limit: ≤100 parts
- Headroom: 47 parts for future archetypes
- Unique configurations: 73,584 (exceeds 50+ target)

## SVG Authoring Rules

### File Structure

```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">
  <g class="body-skin">
    <!-- body paths -->
  </g>
  <g class="outfit-primary">
    <!-- outfit paths -->
  </g>
  <g class="hair-color">
    <!-- hair paths -->
  </g>
</svg>
```

### Naming Conventions

- Named `<g>` elements with CSS class: `.body-skin`, `.outfit-primary`, `.outfit-secondary`, `.hair-color`, `.accessory-color`
- Part files: `{archetype}-{layer}-{variant}.svg` (e.g., `knight-hair-style1.svg`, `dragon-wing-left.svg`)
- One SVG file per swappable part — no multi-part files
- Consistent `viewBox` dimensions within an archetype

### Runtime Recolouring

- Runtime recolouring via CSS `fill` overrides on named `<g>` groups
- MUST use AndroidSVG library to apply CSS overrides
- MUST NOT use Android `ColorFilter` (breaks multi-colour parts)
- Colour palette: each recolourable group has a defined set of allowed colours
- Default colours embedded in SVG; overrides applied at rasterisation time

## Asset Generation Pipeline

### Workflow

1. **Prompt** AI image generator with style reference and part specification
2. **Log** every prompt in `prompt-log.md` (session date, model, prompt text, result assessment)
3. **Validate file format** before any further step — run `PIL.Image.open(f).verify()`. External APIs may return SVG, WebP, or other formats with a `.png` extension. If SVG, render to PNG via `cairosvg.svg2png()` before vision evaluation. Never assume extension == format.
4. **Evaluate** output against quality gates (below)
5. **Clean** generated SVG — remove unnecessary attributes, ensure named groups exist
6. **Test** compositing with other parts (layering, colour overrides)
7. **Archive** in `assets/characters/{archetype}/` or `assets/scenes/{scene-name}/`

### Generation Scripts (tools/rs3/)

| Script | Purpose | Validated |
|---|---|---|
| `n5_recraft_eval.py` | Generate character sprites via Recraft v3 — all styles, delegates to `shared/retrieve_image.py` | 2026-04-16 (N-5), patched 2026-04-17 |
| `n7_scene_regen.py` | Generate scene backgrounds via Recraft v3 — magic-byte format detection, auto SVG→PNG, PIL.verify(), prompt-log append | 2026-04-16 (N-7) |
| `_probe_styles.py` | Probe Recraft API for valid style IDs | 2026-04-16 |
| `_probe_landscape_sizes.py` | Probe Recraft API for valid sizes (confirmed: 1024×1024 only for v4 vector) | 2026-04-16 |

### Shared Image Retrieval Utility (tools/shared/)

**All scripts that download images from external APIs MUST use `tools/shared/retrieve_image.py`.**
See `.github/instructions/safe-image-retrieval.instructions.md` for the mandatory rule.

| Module | Purpose | Capabilities |
|---|---|---|
| `shared/retrieve_image.py` | Safe image download with format detection and validation | Magic-byte detection (PNG/JPEG/WebP/GIF/SVG), extension correction, `PIL.verify()`, SVG→PNG via cairosvg, JPEG/WebP→PNG conversion |

**Import pattern (for scripts in any `tools/{spike}/` subfolder):**
```python
import sys
from pathlib import Path
_TOOLS_DIR = Path(__file__).resolve().parent.parent
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))
from shared.retrieve_image import download_image
```

### Nano Banana API — Investigation in Progress (RS-7)

**Status: ⬜ Under investigation — [RS-7_NanoBananaEvaluation.md](../../docs/investigations/RS-7_NanoBananaEvaluation.md)**  
**Identified:** 2026-04-17 | **ExecPlan:** [exec-plan-rs7.md](../../docs/investigations/exec-plan-rs7.md)

Nano Banana is a REST image-generation gateway. The default model (`nano-banana`) maps to
`gemini-2.5-flash-image` — the same model currently used manually (AD-9) — now accessible
via a scriptable API. It also supports `referenceImageUrls` for image-to-image style anchoring.

| Property | Value |
|---|---|
| Endpoint | `POST https://www.nananobanana.com/api/v1/generate` |
| Auth | `Authorization: Bearer nb_<key>` (own key system — NOT GOOGLE_API_KEY) |
| Default model | `nano-banana` = `gemini-2.5-flash-image` (1 credit) |
| Pro models | `nanobanan-2` (3 cr), `nanobanan-2-2k` (4 cr), `nanobanan-2-4k` (5 cr) |
| Image-to-image | `referenceImageUrls: string[]` — requires **publicly hosted HTTPS URL** |
| Aspect ratio | `aspectRatio` param — valid values NOT documented; probe required (N-2) |
| Output format | Raster PNG only (no SVG) |
| URL lifetime | Generated URLs valid 15 days — download immediately |
| Content safety | `success: false, warning: true` if output triggers filter |

**Generation scripts (tools/rs7/):**

| Script | Purpose |
|---|---|
| `_check_keys.py` | Verify NB_API_KEY, check credit balance, list all models |
| `n2_probe_aspect_ratios.py` | Empirically discover valid `aspectRatio` values; confirm landscape support |
| `n3_scene_test.py` | Generate castle scenes — text-only vs style-anchored comparison |
| `n4_gemini_ab.py` | A/B: exact RS-3 Gemini prompts via API vs manual baseline |
| `n5_sprite_test.py` | Generate princess sprite — compare against Recraft v3 baseline |
| `n6_parts_test.py` | Generate paper-doll parts with anchor-frame prompts; composite + check alignment |
| `n7_model_comparison.py` | default model vs Pro models side-by-side quality comparison |

**Setup:** Add to `tools/.env`:
```
NB_API_KEY=nb_your_key_here
NB_STYLE_ANCHOR_URL=https://...  # public URL of assets/style-reference/canonical-style.jpg
```

**Tooling evaluation table (to be updated as RS-7 completes):**

| Asset type | Candidate | Status | Notes |
|---|---|---|---|
| Scene backgrounds | `nano-banana` (default) | ⬜ N-3, N-4 | Same model as manual Gemini — direct baseline |
| Character sprites | `nano-banana` + anchor | ⬜ N-5 | Compare vs Recraft v3 `vector_illustration` |
| Paper-doll parts | image-to-image anchor | ⬜ N-6 | Follow-up to RS-3 N-9 MISALIGN finding |
| Default vs Pro | `nanobanan-2` | ⬜ N-7 | Credit premium evaluation |

**Reuse pattern for new scenes:** copy `n7_scene_regen.py`, update `SCENES` list with new scene name, slug, output dir, and prompt. All validation and logging is handled by the script.

### Prompt Log Requirement

Every AI generation session MUST have a `prompt-log.md` recording:
- Date and AI model used
- Exact prompt text
- Output assessment (pass/fail per quality gate)
- Iteration notes

**Prompt log location (Phase 2+):** `assets/prompt-log.md` — single top-level log for all Phase 2 work
(Phase 1 archive prompts were not preserved — see RS-3 F-6).

### Recraft v3 Output Formats

Recraft v3 REST API returns different file formats per style — **the Content-Type is always `application/json` with a URL; the downloaded file format depends on style**:

| Style ID | Actual file format | Extension to save | Notes |
|---|---|---|---|
| `vector_illustration` | SVG (valid XML) | `.svg` | ✅ Preferred for Story App |
| `icon` | SVG with gradients/shadows | `.svg` | ⚠️ Marginal — fails flat spec |
| `digital_illustration` | WebP raster | `.webp` | ❌ Rejected — heavy shading |
| `realistic_image` | WebP raster | `.webp` | Out of scope |

**Key rule:** Do not save Recraft outputs with `.png` extension. Detect actual format by magic bytes before saving. For vision analysis, render SVG to PNG via `cairosvg`; convert WebP via `PIL.Image.convert('RGBA').save(..., 'PNG')`.

**Size constraint (AD-8):** Recraft V4 Vector (`vector_illustration`, `icon`) supports **1024×1024 only**. All landscape sizes rejected. Scene background SVGs are generated square and scaled/cropped to the 2000×1340 display by Compose Canvas at runtime.

**Style anchor — text-only:** Recraft REST API has no image-reference parameter. When using carriage-scene-v3 as a style anchor, encode its characteristics in the prompt text: `flat vector kawaii illustration, low-poly geometric shapes, bold black outlines, flat solid colour fills, no gradients, no shadows, no ambient occlusion, no directional lighting, no texture or masonry detail, fairy tale game background art, flat 2D game scene`.

Validated 2026-04-16 (N-5 characters, N-7 scenes). See RS-3 §12.3, §12.4.

### Gemini Image Generation — Landscape Scene Backgrounds (AD-9)

**Use Gemini (manually) for landscape scene backgrounds.** Recraft's 1024×1024 constraint (AD-8) means square-only outputs. Gemini supports 16:9 landscape output, filling the 2000×1340 tablet display natively without cropping.

**Workflow:**
1. Agent generates prompt text (see `tools/rs3/gemini-scene-prompts.md` for 3 MVP scenes, or use `.github/prompts/generate-scene-prompt.prompt.md` for new scenes)
2. Developer pastes prompt into Gemini image generation UI
3. Generate 2–4 variants; select best
4. Check file format (Gemini may return WebP — verify before use)
5. Save as PNG to `assets/archive/scenes/[scene-id]/gemini-[scene-id]-vN.png`
6. Measure exit pixel positions in image editor → update normalised position tables in `gemini-scene-prompts.md`
7. Log in `assets/prompt-log.md`

**Prompt structure (encode in this order):**
1. Style block — flat vector kawaii, no gradients/shadows/texture, 16:9 landscape (constant, copy verbatim from `gemini-scene-prompts.md`)
2. Scene spatial description — camera angle, background elements, main objects at named positions
3. Exit annotations — for each exit: wall/edge position, visual form (arch/door/gap), what leads beyond, "clearly open and unobstructed"
4. Exclusion block — NOT a photo, NOT 3D, NO textures, NO shadows (constant, copy verbatim)

**Exit annotation format (in prompt):**
```
ON THE LEFT WALL at mid-height: a wide rounded archway, open, dark passage visible beyond — exit to castle corridor. The arch must be clearly open and unobstructed.
```

**RS-5 integration:** Once an accepted image is saved, measure the pixel X/Y of each exit zone and record normalised coordinates `x = px/W, y = py/H` in `gemini-scene-prompts.md`. These become `door.position` values in the RS-5 scene template JSON, improving template authoring accuracy.

### Object Sprite Generation (Scene Props)

**Status: Pipeline documented and validated. Production not yet started. See RS-3 CONDITIONAL-PASS rationale.**

Object sprites are interactive scene props (chairs, tables, lamps, toy chest, bookshelf, candle, shield, crown, flower pot, etc.). Each needs a transparent-background RGBA PNG for use in the app's scene canvas (≤15 objects per scene, 3 MVP scenes).

**Generation tool:** Gemini (same as scene backgrounds, AD-9).  
**Format:** Square composition, white/plain background, single object, flat vector kawaii style.  
**BG removal:** `tools/rs3/n8_bg_remove.py` — edge-connected flood fill, auto-calibrated per sprite. Handles white and near-white backgrounds (`dist_thresh=35–40`).

**Workflow for a new object sprite:**
1. Write prompt: `[object name], flat vector kawaii illustration, low-poly geometric shapes, bold black outlines, flat solid colour fills, white background, no gradients, no shadows, no ambient occlusion, single isolated object, fairy tale prop, square composition`
2. Paste into Gemini UI; generate 2–4 variants; select best
3. Check format (`PIL.Image.open(f).verify()`) — Gemini may return WebP; convert to PNG
4. Save to `assets/archive/objects/[scene-slug]/[object-name]-vN.jpg`
5. Run `n8_bg_remove.py` (add entry to `SPRITES` list): output to `[object-name]-vN.png`
6. Log in `assets/prompt-log.md`
7. Apply quality gate checklist (scene backgrounds checklist applies)

**Pending production ("fold into app build-out"):** ~10–15 objects × 3 MVP scenes = 30–45 sprites.  
**Trigger:** Generate each scene's object set when implementing that scene in `:feature:scene`.  
**Backlog entry:** see [android-technical-design.md §19](android-technical-design.md) — RS-3 row, and [governance.md Phase 7 T7.5](governance.md).  
**Pipeline reference:** RS-3 §12.9 (CONDITIONAL-PASS declaration) and RS-3 §12.6 (BG removal batch N-8).

### Background Removal (Character Sprites)

Character sprites are generated as JPEG with white/near-white backgrounds and must be converted to
transparent PNG for use in the app.

**Validated technique (N-4, 2026-04-16):**
- Tool: Python (Pillow + numpy + scipy.ndimage)
- Script: `tools/rs3/bg_remove.py` _(to be created at N-8 batch pass)_
- Parameters: threshold `R≥240, G≥236, B≥230` + 2px `scipy.ndimage.binary_dilation` for fringe cleanup
- Output: RGBA PNG saved alongside source JPEG
- Calibration: Sample background pixel at (0,0) and character's lightest pixel before applying
- Caution: re-calibrate threshold if asset generation tool or background colour changes

**N-4 validation:** Background of `princess-full-v5.jpg` was ~(250, 250, 245) RGB.
Nearest character pixel was (251, 206, 165) — G=206 and B=165 well clear of threshold.
Result: clean transparent PNG with no visible halo.

## Quality Gate Checklists

### Character Parts

- [ ] Flat vector style — no gradients, no painterly elements
- [ ] Consistent outline weight with existing parts
- [ ] Named `<g>` groups for recolourable regions
- [ ] Correct `viewBox` matching archetype specification
- [ ] Clean SVG — no raster images embedded, no unnecessary transforms
- [ ] Composes correctly with all other parts in the same layer stack
- [ ] Recolouring works (CSS fill override produces expected result)

### Scene Backgrounds

- [ ] Flat vector style matching character art
- [ ] Correct resolution for target device (2000x1200 logical pixels)
- [ ] Interactive zones clearly defined (door/portal hotspots)
- [ ] No elements that clash with foreground character Z-order
- [ ] Subtle atmospheric depth cues: lighter/desaturated distant elements, floor plane hints (RS6-D8)
- [ ] Clear playable floor area — must match scene `depthBounds.yMin`–`depthBounds.yMax` range
- [ ] Each new scene requires a depthBounds tuning pass before release (RS6-D13)

### Batch Quality

- 40% failure rate in a batch triggers full regeneration (not selective patching)
- Style consistency across batch is mandatory — no style drift between parts

## Open Questions (From RS-3 / RS-4)

These remain unresolved and should be flagged when encountered:

- **OQ-1:** Final colour palette definition per archetype
- **OQ-2:** Expression set size (3 per feature confirmed, specific expressions TBD)
- **OQ-3:** Scene background interactive zone specification format
- **OQ-4:** Asset versioning strategy for iterative refinement
- **OQ-5:** ~~Authoritative definition of "flat vector style" — is outdoor-carriage the target?~~ → **RESOLVED:** Outdoor-carriage scene is the canonical style reference. Unified flat vector style confirmed (TD-17). Store as `assets/style-reference/canonical-style.jpg`.
- **OQ-6:** ~~Part-compositing vs full-character generation~~ → **RESOLVED (N-9, 2026-04-17):** Archive parts **MISALIGN** at 1:1 scale — not compositable as-is. Parts were generated as independent hero images with no shared anchor. RS-4 must use **full-combination generation** (generate each full character variant directly as one image) or **inpainting** (edit API that repaints only the outfit/hair region on a base body). See RS-3 §12.7.
- **OQ-7:** ~~Render resolution for target device~~ → RESOLVED: 2000×1200 logical pixels
- **OQ-8:** ~~Raster-to-SVG conversion pipeline (Inkscape/VTracer/Potrace) — acceptable fidelity loss if SVG is hard requirement~~ → **RESOLVED:** SVG is a **soft** requirement. PNG fallback is acceptable for complex assets. VTracer pipeline is optional, not mandatory.
- **OQ-9:** ~~Compositing test validation — parts not yet tested for alignment~~ → **RESOLVED (N-9, 2026-04-17):** MISALIGN confirmed. Crown bbox rows 0.29–0.75h (should be top-of-head ~0.04–0.13h). Hair/outfit span full canvas height. All three parts fill most of the 1024×1024 canvas centred. RS-4 cannot reuse archive parts. See RS-3 §12.7, `tools/rs3/n9_part_anchor.py`.

## Recommendations (From RS-3)

Actionable pipeline recommendations awaiting implementation:

- **REC-1:** Resolve open questions before further asset generation
- **REC-2:** Adopt Midjourney v6 with style reference as primary generation tool
- **REC-3:** ~~Establish canonical style reference image (`assets/style-reference/canonical-style.jpg`)~~ → **DONE (N-6, 2026-04-16).** File created at `assets/style-reference/canonical-style.jpg` (initially `carriage-scene-v4.jpg`; updated 2026-04-17 to `carriage-scene-v3.jpg` per stakeholder preference — stronger geometric language and more distinctive low-poly palette).
- **REC-4:** ~~Regenerate throne room and corridor in flat vector style~~ → **DONE (N-7, 2026-04-16). Result: ✅ ALL 4 VARIANTS PASS.** `recraft-throne-room-v1.svg` (recommended) and `recraft-corridor-v1.svg` (recommended) committed. See RS-3 §12.4. Script: `tools/rs3/n7_scene_regen.py`.
- **REC-5:** Use PNG with transparent background for all sprites. Technique validated at N-4 (see Background Removal above).
- **REC-6:** ~~Investigate Recraft v3 for SVG-native character generation~~ → **DONE (N-5, 2026-04-16). Result: ✅ `vector_illustration` RECOMMENDED.** See RS-3 §12.3 and AD-7. SVG output preferred over DALL-E 3 raster for RS-4 paper doll. `digital_illustration` (WebP, heavy gradients) and `icon` (SVG with gradients/shadow) rejected. Script: `tools/rs3/n5_recraft_eval.py`.
- **REC-7:** ~~Conduct compositing test (princess-v5 on carriage-scene-v4) before scaling up~~ → **DONE (N-4, 2026-04-16). Result: ✅ COMPATIBLE.** See RS-3 §12.1 for full findings. Style match STRONG, colour palette COMPLEMENTARY, scale APPROPRIATE, background removal CLEAN.

### Interior Scene Regeneration Notes (for N-7)

Pre-assessment (2026-04-16) of all existing throne room and corridor assets:

| Scene | Best archive version | Style verdict | Regeneration required? |
|-------|---------------------|---------------|----------------------|
| Throne room | `throne-room-v5-eval.jpg` | ❌ EVALUATION-ONLY (RS-5 door markers visible) | Yes — full regeneration |
| Throne room | `throne-room-v10.jpg` | ❌ FAIL (mobile game cartoon art, shaded stone) | Yes — full regeneration |
| Corridor | `corridor-v5.jpg` | ⚠️ MARGINAL — best direction (flat blocks, but atmospheric lighting) | Yes — regeneration with lighting eliminated |
| Corridor interior | `corridor-interior-v8.jpg` | ❌ FAIL (painterly, Gothic vault detail) | Yes — full regeneration |

**Regeneration prompt strategy for DALL-E 3:**
- Attach `assets/style-reference/canonical-style.jpg` as style reference image
- Include in prompt: "flat vector illustration, geometric shapes, flat colour fills, no shadows, no gradients, no texture, no stone masonry detail, no atmospheric lighting, kawaii"
- Include prohibition: "no ambient occlusion, no directional lighting, no photorealism, no painterly effects, no stone block grout detail"
- Include natural archway openings as exit zones (not marked)
