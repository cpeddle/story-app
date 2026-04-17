# Game Systems — Detailed Reference

Companion document to [`SKILL.md`](SKILL.md). Contains detailed rule specifications, state machines, and content constraints.

## Mood Ladder — Detailed Rules

### States

Three states only: **Friendly** → **Neutral** → **Grumpy**

- Directional per character pair (A→B can differ from B→A)
- Default starting mood: Neutral
- Grumpy is a floor — mood MUST NOT go below Grumpy
- Friendly is a ceiling — mood MUST NOT go above Friendly
- Maximum pairs: 6 characters × 5 others ÷ 2 directions = 30 directional pairs

### State Transitions

| Action | Effect |
|--------|--------|
| Positive dialogue outcome | +1 step toward Friendly |
| Negative dialogue outcome | +1 step toward Grumpy |
| Successful Fix | Reset to Neutral (from Grumpy only) |
| Neutral dialogue outcome | No change |

### Mood Affects

- Dialogue tone availability (Grumpy restricts positive tones)
- Character visual expression (facial expression changes)
- Available actions between characters

## Director Mode — Detailed Rules

- Player controls ONE character at a time (the "directed" character)
- All other characters are autonomous (respond via game rules)
- **Freeze on switch:** When player switches directed character, previous character freezes in place
- Director switch is instant — no animation or transition delay
- Directed character indicated by visual highlight (glow, outline, or badge)

## Fixes System — Detailed Specification

### Rules

- Fixes resolve Grumpy mood back to Neutral — NEVER directly to Friendly
- No partial credit — a Fix either succeeds completely or fails completely
- Multiple fix options per situation (player chooses approach)
- Fix options are context-dependent (based on characters involved, objects nearby)
- Failed Fix: mood stays at Grumpy, player can retry with different approach

### Fix Flow

```
Grumpy pair detected → Fix options presented → Player chooses →
  Success → Mood resets to Neutral
  Failure → Mood stays Grumpy, retry available
```

## Dialogue System — Detailed Specification

### Structure

- Conversations are between exactly 2 characters (1 directed + 1 autonomous)
- Directed character initiates; autonomous character responds
- Maximum 6 character traits per character
- Traits influence available dialogue options

### Tone Picker

- Emoji-based tone selection (NOT text labels)
- Tones are mood-restricted:
  - Friendly mood: all tones available
  - Neutral mood: neutral and positive tones available
  - Grumpy mood: only grumpy/neutral tones available
- Tone selection determines dialogue branch and mood outcome

### Dialogue Trees

- Pre-generated offline (NOT runtime generated)
- For tree structure constraints (depth, branches, schema), see the **dialogue-generation** skill
- Every leaf node MUST have a mood outcome that feeds into the Mood Ladder
- Bilingual: EN + NL, idiomatic Dutch (not literal translation)

## Objects — Detailed Specification

### Properties

- Binary state only: each object is in one of exactly 2 states (e.g., open/closed, lit/unlit)
- Single-purpose: each object has exactly ONE action type
- 6 action types: USE, GIVE, TAKE, OPEN, CLOSE, TOGGLE

### Constraints

- Maximum 15 objects per scene
- Objects are scene-bound — they do not transfer between scenes
- Object state persists within session (auto-saved)
- Objects can participate in Fix scenarios

## Characters — Detailed Specification

- Maximum 6 characters per scene
- Paper-doll visual editor for customisation
- 3 archetypes: Knight (humanoid), Princess (humanoid), Dragon (creature)
- Each character has ≤6 traits (influence dialogue, wants, mood tendencies)
- Characters are scene-bound in MVP (no cross-scene movement)

## Wants System — Detailed Specification

- Each character can have active "wants" (desires/goals)
- Wants are stored as keys, resolved to localised display strings
- Fulfilling a want provides mood bonus
- Ignoring a want may trigger mood penalty over time
- Wants are context-dependent (influenced by scene, nearby objects, relationships)

## Navigation — Detailed Specification

- Visual doors/portals connect scenes — tap to transition
- Fixed spawn points per scene entrance
- No free-roam map — scene-to-scene graph navigation only
- Scene transitions are instant (no loading screen in MVP)
- MVP scope: 2-3 scenes connected

## Onboarding — Detailed Specification

- First-time only — triggers on initial app launch
- Guided walkthrough of core mechanics (tap, drag, Director Mode, dialogue)
- Permanent unlocks — once an onboarding step is completed, it never repeats
- Skippable but not reversible
- Stored in DataStore preferences (NOT Room)

## Chaos Button — Detailed Specification

- Triggers a random event in the current scene
- Mood-safe only: MUST NOT push any mood to Grumpy
- Events are neutral or positive in nature
- Examples: object state toggles, character repositions, sound effects
- Cooldown: prevent rapid repeated activation

## Input Model

- **Tap-to-select:** Single tap selects character or object
- **Drag-on-touch:** Long press + drag to move characters/objects
- **Edge-swipe:** Swipe from screen edge for scene navigation
- Touch targets: minimum 2cm (≈56dp) on target device
- No multi-touch in MVP — single-pointer interactions only

## Audio

- SFX only in MVP — no background music
- Sound cues for: mood changes, object interactions, dialogue events, navigation
- SoundPool for low-latency playback
- All audio assets bundled in APK

## Session Model

- Single world / save file in MVP
- Auto-save on every state change (<100ms target)
- No manual save/load UI
- Session resumes exactly where left off

## MVP Content Scope

| Content | Quantity |
|---------|----------|
| Scenes | 2-3 |
| Characters | 4-6 |
| Objects | 10-15 |
| Dialogue trees | Per character pair per scene |
| Art style | Flat vector / SVG |
| Languages | EN + NL |

## Undo Mechanics

- Last action only — single-level undo
- Undo applies to: character moves, object interactions, dialogue choices
- No redo functionality in MVP
