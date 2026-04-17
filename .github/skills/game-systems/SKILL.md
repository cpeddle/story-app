---
name: game-systems
description: 'Game system design rules for the Story App play sandbox. Covers Mood Ladder, Director Mode, Fixes, Dialogue, Objects, Navigation, Onboarding, Chaos Button, Characters, Wants, and content scope. Invoke when implementing or modifying any gameplay mechanic.'
---

# Game Systems — Story App

## When to Use This Skill

Invoke when:
- Implementing or modifying the Mood Ladder, Director Mode, or Fixes system
- Building the dialogue UI or dialogue selection logic
- Adding objects, actions, or scene interactions
- Implementing navigation between scenes
- Working on onboarding flow or the Chaos Button
- Defining character limits, wants, or traits

## Mood Ladder

- Three states only: **Friendly** → **Neutral** → **Grumpy** (directional per character pair)
- Grumpy is a floor, Friendly is a ceiling — mood cannot exceed these bounds
- Dialogue outcomes and successful Fixes drive state transitions

## Director Mode

- Player controls ONE character at a time; all others are autonomous per game rules
- Previous character freezes when switching; switch is instant with no animation
- Directed character indicated by visual highlight

## Fixes System

- Resolves Grumpy mood back to Neutral only (never directly to Friendly)
- No partial credit — success or failure, player can retry with different approach
- Multiple context-dependent fix options per situation

## Dialogue System

- Conversations between exactly 2 characters (1 directed, 1 autonomous)
- Emoji-based tone picker (mood-restricted availability)
- Pre-generated offline dialogue trees; every leaf has a mood outcome
- Bilingual: EN + NL, idiomatic translations

## Objects

- Binary state only (e.g., open/closed, lit/unlit)
- 6 action types: USE, GIVE, TAKE, OPEN, CLOSE, TOGGLE
- Scene-bound; state persists within session

## Characters

- 3 archetypes: Knight, Princess, Dragon
- Maximum 6 characters per scene; ≤6 traits per character
- Scene-bound in MVP (no cross-scene movement)

## Wants System

- Characters have context-dependent active "wants" (desires/goals)
- Wants stored as keys, resolved to localised strings at display time
- Fulfilling provides mood bonus; ignoring may trigger penalty

## Navigation & Onboarding

- Visual doors/portals connect scenes via instant transitions; fixed spawn points per entrance
- Onboarding: first-time only, permanent unlock, skippable but not reversible

## Chaos Button & Audio

- Triggers random mood-safe event (neutral or positive only)
- SFX only in MVP (no background music); SoundPool for playback

## Deep Reference

See [`references.md`](references.md) for detailed per-system rules, state transition tables, flow diagrams, input model, session model, MVP content scope, undo mechanics, and character/object constraints.
