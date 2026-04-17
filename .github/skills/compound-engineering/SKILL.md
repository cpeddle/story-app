---
name: compound-engineering
description: 'Post-task governance self-update skill. Detects new scripts, patterns, conventions, or tools created during a session and proposes updates to existing skills, instructions, prompts, or governance artifacts. Invoke at session end or after completing a significant task to capture learnings and keep governance current.'
---

# Compound Engineering — Story App

## When to Use This Skill

Invoke when:
- An ExecPlan has been completed (mandatory — this is the final step of every ExecPlan)
- A session created new scripts, tools, or utilities that future sessions should know about
- A recurring pattern emerged that should become an instruction or skill rule
- A workaround was discovered that should be documented to prevent rediscovery
- A new dependency, library, or build configuration was introduced
- A design decision was made that should be recorded (new TD-N entry)
- The session is ending and you want to capture learnings before context is lost

## Compound Step — What It Does

After task completion, scan the session for **governable artefacts** — things that should be
wired into the `.github/` governance framework so future agents benefit automatically.

### Detection Checklist

| Signal | Action | Target Artifact |
|--------|--------|-----------------|
| New script created (`.py`, `.sh`, `.kts`) | Add to prompt file or skill reference | `.github/prompts/` or skill `references.md` |
| New build task or Gradle configuration | Update `android-architecture` references or `kotlin-compose` instruction | Skill Layer 3 or instruction |
| New module added | Verify convention plugin applied; update dependency matrix | `android-architecture/references.md` |
| New Room entity or DAO | Update entity table | `android-architecture/references.md` |
| Recurring prompt pattern identified | Create `.prompt.md` file | `.github/prompts/{name}.prompt.md` |
| New design decision (trade-off resolved) | Add TD-N entry | `android-architecture/references.md` |
| New contradiction found between artifacts | Record in Conflict Log + fix both artifacts | `governance.md` Conflict Log |
| New art asset type or pipeline step | Update art-pipeline | `art-pipeline/references.md` |
| New dialogue convention or schema change | Update dialogue-generation | `dialogue-generation/references.md` |
| New game mechanic or rule change | Update game-systems | `game-systems/references.md` |
| New test pattern or testing tool | Update kotlin-compose instruction | `kotlin-compose.instructions.md` |
| Scope violation (feature beyond MVP) | Flag and document deferral rationale | `governance.md` or copilot-instructions |
| Clarifying questions asked (agent or user) | Extract to ExecPlan Q&A patterns | `compound-engineering/references.md` Q&A Log |
| User steering / mid-session corrections | Extract underlying assumption gap | `compound-engineering/references.md` Q&A Log |
| `chub annotate` called in session | Mirror annotation to api-docs/references.md Annotation Log | `api-docs/references.md` |
| api-docs skill returned no/unusable result | Log to api-docs/references.md Skill Failure Log; invoke compound-engineering to classify gap and propose fix (add fallback URL, seed annotation, or raise chub PR) | `api-docs/references.md` |
| New shared utility created in `tools/shared/` | Update art-pipeline and/or relevant skill references; create instruction file if safety-critical | `art-pipeline/references.md`, `.github/instructions/` |
| Agent stuck in retry loop (same action ≥3 times) | Root-cause the failure; create instruction or shared utility to prevent recurrence | `.github/instructions/`, `tools/shared/` |

### Process

1. **Detect** — Review session changes against the detection checklist
2. **Harvest Q&A** — Review the session for clarifying questions and steering corrections (see below)
3. **Classify** — For each finding, determine: skill update / instruction update / new prompt / governance log / Q&A pattern
4. **Propose** — Present changes to the developer with rationale and target artifact
5. **Apply** — After approval, make the edits following the rules below
6. **Validate** — Cross-reference updated artifact against related artifacts for contradictions

### Session Q&A Review

Review the session for **questions and steering decisions** that reveal gaps in upfront planning.
These feed into future ExecPlan creation by identifying what should be asked before work begins.

**Sources to review:**

| Source | How to Capture | What to Extract |
|--------|---------------|-----------------|
| Agent clarifying questions (via ask-questions tool) | Agent has context of its own tool calls within the session | The question, the options presented, the answer chosen |
| User steering corrections ("no, do X instead", "wrong approach") | User messages that redirect the agent mid-task | The assumption that was wrong, the correction applied |
| Ambiguities that caused rework | Detected when agent had to redo work after clarification | The missing context that would have prevented the rework |
| Design trade-offs resolved via discussion | User/agent back-and-forth evaluating options | The trade-off, the decision, the rationale |

**Capture rule:** During the session, write Q&A observations to session memory (`/memories/session/qa-capture.md`)
for within-session scratch notes. At compound step time, harvest these into the Q&A Log in [`references.md`](references.md).
**Important:** Session memory is ephemeral — it is cleared when the VS Code session ends. For findings
that must survive across sessions (recurring patterns, critical corrections), write directly to
`/memories/repo/` (durable repository memory) or to the Q&A Log in [`references.md`](references.md).

**Output:** Each captured Q&A becomes a candidate **upfront question** for future ExecPlans:
- If the same type of question recurs across sessions → promote to ExecPlan template
- If a user correction reveals a systematic assumption gap → add as a required clarification

> **Limitation:** Agents cannot retrospectively read full session transcripts or debug logs.
> Q&A capture relies on: (1) the agent's in-context memory of the current session, and
> (2) explicit notes written to `/memories/session/` during the session. The compound step
> should be invoked while the session context is still live.

### Update Rules

- **Never delete existing rules** without explicit developer approval
- **Append, don't rewrite** — add new entries to existing tables/lists rather than restructuring
- **Maintain Layer 2/3 balance** — keep SKILL.md concise (≤80 lines); verbose detail goes in references.md
- **Record lineage** — note which session or task produced the update (e.g., "Added by compound step, session 2026-04-13")
- **Check for contradictions** — after every update, verify the changed artifact doesn't conflict with overlapping artifacts
- **Update governance.md** — if a new artifact is created or an existing one significantly changes, record it

### Prompt File Convention

When a recurring workflow is identified (≥2 occurrences), create a prompt file:

```
.github/prompts/{name}.prompt.md
```

Prompt files are lightweight task templates invoked via `/prompt-name` in chat.
They contain context setup + task instructions but no persistent rules (those belong in instructions/skills).

## ExecPlan Integration

This skill is the **mandatory final step** of every ExecPlan. After all plan tasks are marked ✅:

1. Run the full compound detection checklist against the ExecPlan's outputs
2. Harvest session Q&A into the Q&A Log
3. Propose governance updates
4. Update the ExecPlan's status to ✅ Complete only after compound step is done

**ExecPlan creation feedback loop:** When creating a new ExecPlan, consult the Q&A Log in
[`references.md`](references.md) to identify upfront questions that should be asked during planning.
Recurring Q&A patterns indicate missing preconditions or ambiguous scope.

## Governance Wiring

This skill operates on the governance framework documented in [`governance.md`](../../../docs/investigations/governance.md).

Key artifacts it may update:
- `.github/copilot-instructions.md` — project-wide rules
- `.github/instructions/*.instructions.md` — file-pattern coding standards
- `.github/skills/*/SKILL.md` — domain skill Layer 2
- `.github/skills/*/references.md` — domain skill Layer 3
- `.github/prompts/*.prompt.md` — reusable task templates
- `docs/investigations/governance.md` — audit trail and conflict log

## Deep Reference

See [`references.md`](references.md) for the full compound workflow, example scenarios, and governance artifact inventory.
