---
name: dialogue-generation
description: 'Dialogue tree JSON schema, bilingual generation rules (EN+NL), content filtering, and evaluation rubric for Story App. Invoke when generating dialogue trees, validating dialogue JSON, implementing the dialogue engine, or evaluating dialogue quality.'
---

# Dialogue Generation — Story App

## When to Use This Skill

Invoke when:
- Generating dialogue tree JSON files
- Validating dialogue against the schema or evaluation rubric
- Implementing the dialogue engine in `:domain`
- Working with bilingual content (EN + NL)
- Integrating content filtering (TD-13)
- Evaluating dialogue quality for acceptance

## Approach: Offline Pre-Generation (Recommended)

- Dialogue trees are **pre-generated offline** and bundled as JSON assets
- NOT generated at runtime on device
- NOT fetched from a cloud API
- This is the lowest-risk approach per RS-2 assessment
- Stored in: `assets/dialogue_en.json`, `assets/dialogue_nl.json`

## Schema Overview

Dialogue nodes form a tree with root branches leading to leaf outcomes:

| Constraint | Value |
|-----------|-------|
| Tree depth | 2–3 levels |
| Branches per node | 2–4 |
| Root branches | ≥3 |
| Participants | Exactly 2 |
| Leaf outcome | Required: MOOD_POSITIVE, MOOD_NEGATIVE, or NEUTRAL |

**Speaker alternation:** Speakers SHOULD alternate between nodes.

See [`references.md`](references.md) for full JSON example and Kotlin data classes.

## Bilingual Rules (EN + NL)

**English (EN):** Primary language, Grade 2.5 reading level max, simple subject-verb-object structure.

**Dutch (NL):** Idiomatic (not literal translation), Flesch-Douma ≥70, familiar children's vocabulary, verb-second in main clauses.

**Workflow:** Generate EN tree → generate NL variant → validate both independently → verify tone consistency.

See [`references.md`](references.md) for full bilingual workflow detail.

## Content Filtering (TD-13)

- On-device TFLite model for content safety
- Runs at generation time during offline authoring
- Checks: violence, fear, inappropriate themes, bullying language
- Flagged content: reject and regenerate (hard gate, no overrides)

## Hard Gates (All Must Pass)

Failure on ANY gate = reject entire tree:

1. JSON schema valid
2. All paths terminate at leaf nodes with outcomes
3. ≥3 branches at root
4. ≥2 levels deep on at least one path
5. Every leaf has MOOD_POSITIVE, MOOD_NEGATIVE, or NEUTRAL
6. Vocabulary: ≤Grade 2.5 (EN) / Flesch-Douma ≥70 (NL)
7. Passes on-device content safety check

## Deep Reference

See [`references.md`](references.md) for full JSON schema example, Kotlin data class definitions, outcome value semantics, detailed bilingual workflow, content filtering implementation, quality scoring rubric (soft gates), and unresolved open questions from RS-2.
