---
description: "Generate a Gemini image generation prompt for a new Story App scene. Encodes the canonical flat vector kawaii style and positions exits, doors, and objects at explicit spatial locations."
---

You are generating a Gemini image generation prompt for a new scene background in the Story App.

## Story App Art Rules

The Story App uses a strict flat vector kawaii art style. Every scene prompt MUST encode these constraints:

**Style rules (non-negotiable):**
- Flat vector kawaii — low-poly geometric shapes, bold black outlines on all forms
- Flat solid colour fills — absolutely NO gradients, NO shadows, NO ambient occlusion, NO directional lighting
- NO surface texture, NO masonry/brickwork detail, NO depth-of-field blur, NO photorealism
- Warm fairy-tale colour palette: soft golds, peach, warm blues, bright greens, cream
- 16:9 landscape orientation (for tablet display 2000×1340px)
- Canonical style reference: `assets/style-reference/canonical-style.jpg` (outdoor carriage scene)

**Exit / door rules:**
- Every exit (arch, door, path gap) must be explicitly described with its **wall position** (left wall / right wall / far end / left edge / right edge)
- The exit must be described as **clearly open and unobstructed** — a character sprite must be able to stand at the exit without overlap
- For archways: specify "open, dark passage visible beyond" or "open, bright outdoor sky beyond"
- For doors: specify "large wooden door with geometric panels and round handle"
- For outdoor gaps: specify "clear wide gap between trees/rocks/boundary at ground level"

---

## What I need from you

Answer the following questions about the NEW scene, then I will produce the complete Gemini prompt.

1. **Scene name and ID** — e.g., "Castle Kitchen" / `castle-kitchen`
2. **Camera view** — side view? front view? looking down a corridor? elevated from front?
3. **Background elements** — what fills the back wall / horizon / upper area?
4. **Main props / objects** — what is the key interactive object in this scene? Where does it sit (centre, left, right)?
5. **Floor / ground** — what covers the floor (carpet, tiles, grass, cobblestone)?
6. **Exits** — list each exit with: wall/edge it's on, what it leads to, visual form (arch / door / path gap / stairs)
7. **Colour palette** — any specific colours for this room/outdoor space?
8. **Any objects to foreground** — things to place in front (benches, pots, toys)?

---

## Output format I will produce

For each scene, I will output:

### 1. Gemini image prompt (copy-paste ready)

A single paragraph prompt combining all style constraints, spatial description, exit placements, and exclusion block.

### 2. RS-5 exit position table (pre-generation estimate)

| Exit | Estimated Norm X | Estimated Norm Y | Notes |
|------|-----------------|-----------------|-------|
| [exit name] | ~0.XX | ~0.XX | [hint] |

These are pre-generation estimates. Measure actual pixel coordinates from the accepted image and update `tools/rs3/gemini-scene-prompts.md`.

### 3. RS-5 text description draft

A single paragraph in the format of `tools/rs5/text-descriptions/outdoor-carriage.txt` — spatial prose description of the scene for future RS-5 template pipeline input.

---

## Reference scenes

If asking about an already-defined scene, see `tools/rs3/gemini-scene-prompts.md` for:
- `outdoor-carriage` — canonical style reference
- `castle-throne-room` — interior, two arched exits
- `castle-corridor` — long corridor, two foreground doors + far archway
