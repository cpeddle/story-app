# Gemini Scene Prompts — Story App MVP Scenes

**Purpose:** Ready-to-paste prompts for Gemini image generation (landscape format).  
**Target:** 16:9 landscape, flat vector kawaii style, exits and objects at defined spatial positions.  
**Usage:** Paste a prompt into Gemini's image generation UI. Generate 2–4 variants. Select best. Save as PNG. Record in `assets/prompt-log.md`.

---

## Style Primer

This block is reused across every scene prompt. Keep it verbatim — do not rephrase.

```
Flat 2D game background for a children's fairy-tale tablet game. Style: flat vector kawaii. Low-poly geometric shapes. Bold black outlines on all forms. Flat solid colour fills throughout — absolutely no gradients, no shadows, no ambient occlusion, no directional lighting, no surface texture, no masonry or brickwork detail. No depth-of-field blur. No photorealism. Clean simple geometric shapes only. Warm fairy-tale colour palette: soft golds, peach, warm blues, bright greens, cream. 16:9 landscape orientation.
```

---

## Exclusion Block

Append this to the end of every scene prompt:

```
This is NOT a photo, NOT 3D rendered, NOT a painted illustration, NOT a mobile RPG background. NO realistic stone textures. NO atmospheric fog or bloom lighting. NO specular highlights. NO cast shadows. Flat coloured geometry only.
```

---

## Scene 1 — Outdoor Carriage Area

**Scene ID:** `outdoor-carriage`  
**Connection map:** Exit left → castle gate path | Exit right → garden path

### Intended exit positions (for RS-5 template authoring after generation)

| Exit | Normalised X | Normalised Y | Notes |
|------|-------------|-------------|-------|
| Exit left (castle gate) | 0.08 | 0.76 | **Measured from gemini-outdoor-carriage.png** — clear ground-level gap left trees |
| Exit right (garden path) | 0.91 | 0.76 | **Measured** — matching right gap |

### Prompt

```
Flat 2D game background for a children's fairy-tale tablet game. Style: flat vector kawaii. Low-poly geometric shapes. Bold black outlines on all forms. Flat solid colour fills throughout — absolutely no gradients, no shadows, no ambient occlusion, no directional lighting, no surface texture, no masonry or brickwork detail. No depth-of-field blur. No photorealism. Clean simple geometric shapes only. Warm fairy-tale colour palette: soft golds, peach, warm blues, bright greens, cream. 16:9 landscape orientation.

A countryside road scene viewed from the side. A wide cobblestone path made of flat geometric stone shapes runs along the bottom of the image from the left edge to the right edge. In the right-centre area of the path, a royal carriage with large circular wooden wheels sits parked — the carriage body is a geometric boxy shape in gold and red with a flat roof. Rolling green hills built from triangular low-poly planes fill the background, with a winding path leading toward a small castle with pointed towers on a hilltop in the upper-right background. Tall stylised geometric trees flank both sides of the scene.

ON THE LEFT SIDE: there is a clear wide gap between the left-side trees at ground level, wide enough for a character to walk through — this is the exit to the castle gate. The gap must be visible and unobstructed.
ON THE RIGHT SIDE: there is a matching clear wide gap between the right-side trees at ground level — this is the exit to the garden path. The gap must be visible and unobstructed.

Warm peach-orange sky with simple geometric clouds. Bright greens, teal-blue sky accents, gold carriage.

This is NOT a photo, NOT 3D rendered, NOT a painted illustration, NOT a mobile RPG background. NO realistic stone textures. NO atmospheric fog or bloom lighting. NO specular highlights. NO cast shadows. Flat coloured geometry only.
```

---

## Scene 2 — Castle Throne Room

**Scene ID:** `castle-throne-room`  
**Connection map:** Exit left arch → castle corridor | Exit right arch → second wing / courtyard

### Intended exit positions (for RS-5 template authoring after generation)

| Exit | Normalised X | Normalised Y | Notes |
|------|-------------|-------------|-------|
| Left archway (corridor) | 0.10 | 0.62 | **Measured from gemini-castle-throne-room.png** — dark passage, arch clearly open |
| Right archway (second wing) | 0.89 | 0.62 | **Measured** — matching rounded arch |

### Prompt

```
Flat 2D game background for a children's fairy-tale tablet game. Style: flat vector kawaii. Low-poly geometric shapes. Bold black outlines on all forms. Flat solid colour fills throughout — absolutely no gradients, no shadows, no ambient occlusion, no directional lighting, no surface texture, no masonry or brickwork detail. No depth-of-field blur. No photorealism. Clean simple geometric shapes only. Warm fairy-tale colour palette: soft golds, peach, warm blues, bright greens, cream. 16:9 landscape orientation.

The interior of a castle throne room viewed from the front, showing the full width of the room. A large ornate throne sits centred on a low raised dais at the back of the room — the throne has geometric carved shapes and a tall back, in gold and deep red. A long red carpet with a simple geometric border pattern runs from the centre foreground directly to the throne steps. Geometric stone columns flank the throne on both sides. Wall-mounted torches with bold flat flame shapes hang on the walls. Decorative gold and blue banners hang from the upper walls. The ceiling has simple geometric arched vaulting. The floor is made of large flat-coloured square stone tiles with a simple two-tone geometric pattern.

ON THE LEFT WALL, at mid-height (roughly two-thirds up the wall, near the left edge of the image): a wide rounded archway is cut into the wall, open and dark beyond — this is the exit leading to the castle corridor. The arch must be clearly open with a dark blue passage visible inside it. The arch should be about one-fifth the width of the image.
ON THE RIGHT WALL, at the same mid-height position (near the right edge of the image): a matching wide rounded archway cut into the right wall, open and dark beyond — this is the exit to the second wing. Same proportions as the left arch.

Warm gold and navy blue colour palette. Cream and gold floor. Stone surfaces are flat solid colour geometric blocks only — NOT textured, NOT shaded, NOT realistic stone.

This is NOT a photo, NOT 3D rendered, NOT a painted illustration, NOT a mobile RPG background. NO realistic stone textures. NO atmospheric fog or bloom lighting. NO specular highlights. NO cast shadows. Flat coloured geometry only.
```

---

## Scene 3 — Castle Corridor

**Scene ID:** `castle-corridor`  
**Connection map:** Exit left door → bedroom A | Exit right door → bedroom B | Exit far end → outdoor carriage area

### Intended exit positions (for RS-5 template authoring after generation)

| Exit | Normalised X | Normalised Y | Notes |
|------|-------------|-------------|-------|
| Left foreground door (bedroom A) | 0.13 | 0.66 | **Measured from gemini-castle-corridor-pass2.png** |
| Right foreground door (bedroom B) | 0.87 | 0.66 | **Measured** — matches left door |
| Far end archway (outdoor) | 0.50 | 0.52 | **Measured** — flat warm fill, clearly open |

### Prompt

```
Flat 2D game background for a children's fairy-tale tablet game. Style: flat vector kawaii. Low-poly geometric shapes. Bold black outlines on all forms. Flat solid colour fills throughout — absolutely no gradients, no shadows, no ambient occlusion, no directional lighting, no surface texture, no masonry or brickwork detail. No depth-of-field blur. No photorealism. Clean simple geometric shapes only. Warm fairy-tale colour palette: soft golds, peach, warm blues, bright greens, cream. 16:9 landscape orientation.

The interior of a long straight castle corridor viewed from one end, looking toward the opposite far end. The corridor extends in a long perspective toward a bright opening at the far end. The ceiling has simple geometric vaulted arches repeated along the corridor length. A red carpet runner with a simple geometric border pattern runs down the centre of the flat-colour stone floor. Wall-mounted torches with bold flat flame shapes hang at regular intervals on both walls. Gold and blue decorative banners hang between the torches.

ON THE LEFT WALL in the foreground (near the left edge, roughly two-thirds up the wall): a large wooden door with bold geometric rectangular panels is set into the wall — this is the door to the bedroom on the left. The door should have a simple round brass handle and be clearly a door, not a window.
ON THE RIGHT WALL in the foreground (matching position, near the right edge): a matching wooden door — this is the door to the bedroom on the right. Same style as the left door.
AT THE FAR END of the corridor (centre of the image, furthest away): a bright open archway, noticeably brighter than the corridor interior, showing a warm outdoor sky beyond — this is the exit leading outside to the carriage area. The arch should be clearly open and bright, drawing the eye down the corridor.

The stone walls and floor must be flat solid colour blocks only, slightly different tones to distinguish them — do NOT add texture, do NOT shade the stone, do NOT add mortar lines. Warm cream and grey floor. Navy blue walls with gold accent bands.

IMPORTANT: The entire floor must be a single flat colour — do NOT darken the floor edges or corners. Do NOT add any shadow band along the floor edges. The far-end archway must be a bright flat colour (warm peach or sky blue) with a bold black arch outline — do NOT add bloom, glow, haze, or atmospheric light spill around it. Every surface in the image must be a flat solid fill with zero variation across its area.

This is NOT a photo, NOT 3D rendered, NOT a painted illustration, NOT a mobile RPG background. NO realistic stone textures. NO atmospheric fog or bloom lighting. NO specular highlights. NO cast shadows. NO floor edge darkening. NO perspective-fade gradients. Flat coloured geometry only.
```

---

## Post-Generation Checklist

After generating each scene:

- [ ] **Format check:** Verify file is PNG (not WebP — Gemini sometimes returns WebP). Check with `file` or magic bytes.
- [ ] **Style check:** Does it match the outdoor-carriage canonical style? Flat fills, black outlines, no gradients/shadows?
- [ ] **Exit check:** Are the exit gaps/arches clearly visible and unobstructed? A character sprite must be able to stand at the exit point without overlap.
- [ ] **Object check:** Is the carriage / throne / corridor geometry correct? Not distorted?
- [ ] **Resolution:** Is it ≥1920×1080? (Gemini typically outputs at high resolution — confirm.)
- [ ] **Save:** `assets/archive/scenes/[scene-id]/gemini-[scene-id]-v1.png` (increment version on retry)
- [ ] **Log:** Append to `assets/prompt-log.md` with variant number selected and any style notes
- [ ] **RS-5 exit annotation:** Record the actual pixel X/Y of each exit in this file (update the normalised position tables above once you can measure them from the image)

---

## RS-5 Exit Annotation Workflow

After accepting an image, measure the exit positions in an image editor and record them here. This becomes the ground truth for RS-5 template authoring.

**How to measure:**
1. Open the image in any image editor
2. Hover over the centre of each exit zone (arch opening, door centre, path gap)
3. Note the pixel coordinates `(px, py)` and the image dimensions `(W, H)`
4. Normalised position: `x = px / W`, `y = py / H`

Once measured, update the normalised position tables in this file and proceed to RS-5 template JSON authoring using those coordinates as `door.position` values.
