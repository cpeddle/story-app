---
description: 'Manage a research spike: resolve open questions, delegate analysis, update the RS document and governance artifacts.'
---

# Manage Research Spike

Manage the research spike specified by the user. Maintain oversight, ask clarifying questions, and ensure all governance artifacts stay current.

## Inputs

- **RS document** — the `docs/investigations/RS-*.md` file to manage
- **Stage focus** — which stage(s) to advance (default: next incomplete stage)

## Workflow

### 1. Gather Context

- Read the RS document fully
- Read the compound-engineering skill: `.github/skills/compound-engineering/SKILL.md`
- Read the kotlin-compose instructions: `.github/instructions/kotlin-compose.instructions.md`
- Read relevant skill SKILL.md and references.md files (android-architecture, art-pipeline, game-systems, dialogue-generation — as applicable to the spike topic)
- Read `docs/investigations/android-technical-design.md` sections relevant to the spike

### 2. Resolve Open Questions

- Review the RS document's OQ list and Decision Log
- Ask the stakeholder clarifying questions for any OQs that block the current stage
- Record resolved OQs and new decisions (RS*-D*) in the RS document
- Update the RS document status line

### 3. Delegate Analysis

Delegate independent analyses as subagents in parallel where possible:

- **Architecture impact analysis** — module placement, model changes, Room migration, rendering changes, performance assessment, contradiction check against existing TDs
- **Stage prototype specification** — file structure, data classes, composable/function specs, unit tests, test scenarios, success gate criteria

Capture agent outputs and apply findings to the RS document sections.

### 4. Update RS Document

Apply findings from delegated analysis to the relevant sections:

- Proposed model changes (data classes, entities)
- Implementation considerations (rendering, touch handling, performance)
- Research plan stage expansion (detailed spec, tests, success gates)
- Deduplicate any content that became redundant after updates
- Cross-reference between sections rather than repeating information

### 5. Update Governance Skills

For each skill affected by the spike's findings:

| Skill | Update When |
|-------|------------|
| `android-architecture` | New model classes, module placement, rendering changes, performance notes |
| `art-pipeline` | New art requirements, style rule clarifications, quality gate items |
| `game-systems` | New mechanics, interaction rules, gameplay changes |
| `dialogue-generation` | Schema changes, new dialogue conventions |

Rules:
- Append to existing tables/lists — do not restructure
- Keep SKILL.md concise (≤80 lines); detail goes in references.md
- Check for contradictions with overlapping artifacts after each update

### 6. Update Governance Audit Trail

Add a new task entry to `docs/investigations/governance.md`:

```
### T{N}.{M}: RS-{X} — {Brief Description} ✅

**Scope:** {What was managed}
**Action:**
- {List of actions taken — OQs resolved, analyses delegated, sections updated}
**Findings:**
- {Key technical findings from analysis}
**Artifacts updated:** {List of files changed}
```

### 7. Compound-Engineering Detection

Run the detection checklist from `.github/skills/compound-engineering/SKILL.md`:

- New scripts, build tasks, modules, Room entities, design decisions?
- New contradictions between artifacts?
- Recurring patterns that warrant a new `.prompt.md`?
- Scope violations beyond confirmed MVP?

Flag findings to the stakeholder. Apply non-controversial updates; propose others for review.

## Completion Criteria

- [ ] All OQs blocking the current stage are resolved
- [ ] RS document sections updated with delegated analysis findings
- [ ] Relevant governance skills updated (SKILL.md and/or references.md)
- [ ] Governance audit trail entry added
- [ ] Compound-engineering detection checklist run — no unrecorded artifacts
- [ ] RS document status line reflects current state
