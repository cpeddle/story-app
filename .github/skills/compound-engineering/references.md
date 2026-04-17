# Compound Engineering — References

Companion document to [`SKILL.md`](SKILL.md). Contains the full compound workflow, example scenarios,
and governance artifact inventory for post-task self-update.

## Full Compound Workflow

Adapted from the EveryInc Compound Engineering pattern (T5.2), simplified for single-developer
agentic workflow with centralised governance.

### Phase Flow

```
ExecPlan Complete (or session ending) →
  Detect Governable Artefacts →
  Harvest Session Q&A (from context + /memories/session/) →
  Classify Updates →
  Propose to Developer →
  Apply (after approval) →
  Validate Cross-References →
  Log in governance.md (if significant) →
  Mark ExecPlan ✅ Complete
```

### Detection Heuristics

Scan session activity for these signals:

#### Code Artefacts
- **New files created** — especially scripts, utilities, config files outside standard module structure
- **New modules** — verify convention plugin applied, add to dependency matrix
- **New entities/DAOs** — update Room entity table in android-architecture references
- **New Composables** — check if pattern is reusable; if so, note in kotlin-compose instruction
- **New test patterns** — if a testing approach is novel, add to kotlin-compose testing section

#### Process Artefacts
- **Workarounds discovered** — document the problem and solution so agents don't rediscover it
- **Prompt patterns** — if you wrote a detailed prompt that could be reused, extract to `.prompt.md`
- **Design decisions** — if a trade-off was evaluated and resolved, assign a TD-N ID and log it
- **Scope decisions** — if something was explicitly deferred, record the rationale

#### Governance Artefacts
- **Contradictions found** — between any two `.github/` files → fix both + add to Conflict Log
- **Missing coverage** — rule that should exist but doesn't → add to appropriate artifact
- **Stale rules** — rule that no longer applies → propose removal with rationale

### Classification Matrix

| Finding Type | Target | Action |
|-------------|--------|--------|
| Reusable script/tool | `.github/prompts/{name}.prompt.md` | Create prompt file linking to the script |
| Build/config pattern | `kotlin-compose.instructions.md` or skill references | Append rule or example |
| New entity/DAO/module | `android-architecture/references.md` | Update table/matrix |
| Game rule change | `game-systems/references.md` | Update relevant section |
| Art pipeline change | `art-pipeline/references.md` | Update relevant section |
| Dialogue schema change | `dialogue-generation/references.md` | Update relevant section |
| Design decision | `android-architecture/references.md` TD table | Add TD-N entry |
| Cross-cutting project rule | `copilot-instructions.md` | Add/modify rule |
| Contradiction | Both conflicting files + `governance.md` Conflict Log | Fix + log |
| New convention | Appropriate instruction file | Add rule |
| Deferred feature | `governance.md` or copilot-instructions scope section | Record deferral |

## Example Scenarios

### Scenario 1: Python Script Created for Asset Processing

**Session activity:** Developer creates `scripts/svg_cleanup.py` to batch-clean SVG files.

**Compound step:**
1. **Detect:** New `.py` file created outside standard Kotlin module structure
2. **Classify:** Reusable tool → prompt file + art-pipeline reference update
3. **Propose:**
   - Create `.github/prompts/svg-cleanup.prompt.md` with usage instructions
   - Add script reference to `art-pipeline/references.md` under Asset Generation Pipeline
4. **Apply:** Create prompt file, update references.md
5. **Validate:** No contradictions — additive change

### Scenario 2: New Room Entity Added

**Session activity:** `WantEntity` added to `:data` module.

**Compound step:**
1. **Detect:** New `@Entity` class in `:data`
2. **Classify:** Entity table update → android-architecture references
3. **Propose:** Add row to Room Entities table: `WantEntity | :data | Active character wants and fulfillment state`
4. **Apply:** Update references.md entity table
5. **Validate:** Check game-systems references for consistency

### Scenario 3: Recurring Dialogue Validation Prompt

**Session activity:** Developer has manually prompted dialogue validation 3 times with similar instructions.

**Compound step:**
1. **Detect:** Repeated prompt pattern (≥2 occurrences)
2. **Classify:** Recurring workflow → prompt file
3. **Propose:** Create `.github/prompts/validate-dialogue-tree.prompt.md` with standard validation steps
4. **Apply:** Create prompt file referencing dialogue-generation skill hard gates
5. **Validate:** Prompt file references correct schema constraints

### Scenario 4: Design Decision During Implementation

**Session activity:** Chose `rememberSaveable` over `DataStore` for character editor undo stack.

**Compound step:**
1. **Detect:** Trade-off evaluated and resolved during implementation
2. **Classify:** Design decision → TD entry
3. **Propose:** Add `TD-16: rememberSaveable for character editor undo (not DataStore)` to TD table
4. **Apply:** Update android-architecture/references.md
5. **Validate:** Check game-systems undo section for consistency

### Scenario 5: Session Q&A Reveals Missing ExecPlan Precondition

**Session activity:** Agent asks "Should the SVG cleanup script target all archetypes or just humanoid?"
Developer answers "All archetypes." Later, agent asks "Should cleaned SVGs overwrite originals or write
to a new directory?" Developer answers "New directory — never overwrite originals."

**Compound step:**
1. **Detect:** Two clarifying questions mid-session that could have been asked upfront
2. **Classify:** Q&A pattern → ExecPlan precondition candidates
3. **Propose:**
   - Add to Q&A Log: "When building asset-processing scripts, ask upfront: (a) scope (which archetypes), (b) file handling (overwrite vs copy)"
   - If pattern recurs, promote to ExecPlan template question
4. **Apply:** Append to references.md Q&A Log
5. **Validate:** No contradictions — additive observation

### Scenario 6: User Steering Correction Reveals Assumption Gap

**Session activity:** Agent begins implementing dialogue validation as a Kotlin unit test. Developer
says "No, this should be a standalone Python script — it runs during offline authoring, not in the
Android test suite." Agent pivots.

**Compound step:**
1. **Detect:** User correction redirected implementation approach mid-task
2. **Classify:** Assumption gap → Q&A pattern + possible skill update
3. **Propose:**
   - Add to Q&A Log: "When implementing validation tooling, ask upfront: runtime (Android test) vs offline (standalone script)?"
   - Update dialogue-generation SKILL.md or references.md to clarify that validation tooling is offline Python, not Kotlin tests
4. **Apply:** Append Q&A Log entry + update skill if needed
5. **Validate:** Check consistency with content filtering timing (offline + runtime)

## Governance Artifact Inventory

Current artifacts that the compound step may update:

| Artifact | Path | Type | Lines |
|----------|------|------|-------|
| Project instructions | `.github/copilot-instructions.md` | copilot-instructions | ~80 |
| Conventional commits | `.github/instructions/conventional-commits.instructions.md` | instruction | ~60 |
| Kotlin/Compose | `.github/instructions/kotlin-compose.instructions.md` | instruction | ~77 |
| Android Architecture | `.github/skills/android-architecture/SKILL.md` | skill L2 | ~93 |
| Android Architecture refs | `.github/skills/android-architecture/references.md` | skill L3 | ~70 |
| Game Systems | `.github/skills/game-systems/SKILL.md` | skill L2 | ~50 |
| Game Systems refs | `.github/skills/game-systems/references.md` | skill L3 | ~127 |
| Art Pipeline | `.github/skills/art-pipeline/SKILL.md` | skill L2 | ~46 |
| Art Pipeline refs | `.github/skills/art-pipeline/references.md` | skill L3 | ~107 |
| Dialogue Generation | `.github/skills/dialogue-generation/SKILL.md` | skill L2 | ~51 |
| Dialogue Generation refs | `.github/skills/dialogue-generation/references.md` | skill L3 | ~137 |
| Compound Engineering | `.github/skills/compound-engineering/SKILL.md` | skill L2 | ~75 |
| Compound Engineering refs | `.github/skills/compound-engineering/references.md` | skill L3 | this file |
| API Docs | `.github/skills/api-docs/SKILL.md` | skill L2 | ~88 |
| API Docs refs | `.github/skills/api-docs/references.md` | skill L3 | ~100 |
| Governance audit trail | `docs/investigations/governance.md` | governance | ~500 |

## Compound Learning Log

Append entries here as the compound step captures learnings across sessions.

| Date | Session Summary | Finding | Action Taken | Artifact Updated |
|------|----------------|---------|--------------|------------------|
| 2026-04-13 | Phase 5 ExecPlan | Compound Engineering skill created | New skill wired into governance | This file + governance.md |
| 2026-04-15 | RS-5 Evaluation ExecPlan (T1–T12) | New reusable eval harness `tools/llm-eval/` + RS-5 scorer created; 316 trials executed; GT corrections needed; two-pass bug found pre-execution | Added RS5-D9–D18 to RS-5 §15; exec-plan §7 populated with Stage 1–2b results + GT correction + code fix log | RS-5_LLMSceneTemplatePipeline.md §15, exec-plan-rs5-evaluation.md §7 |
| 2026-04-16 | RS-5 Post-Evaluation Architectural Analysis | Discovered that door detection responsibility belongs to developer (nav graph), not model; three options (A/B/C) evaluated; Option C `{scene_type_constraints}` prompt pattern identified as reusable convention | Added RS5-D19–D23 to RS-5 §15; OQ-11 added to §16; D-EC1–5 logged in exec-plan §7; visual ambiguity caveat added to §13.2 | RS-5_LLMSceneTemplatePipeline.md §13.2/§15/§16, exec-plan-rs5-evaluation.md §7 |
| 2026-04-16 | RS-3 N-5 Recraft evaluation (session recovery) | Recraft returns SVG/WebP files that were saved with `.png` extension by the generation script. Agent vision analysis loop stalled indefinitely retrying corrupted-looking files. Root cause: the files were valid SVG/WebP, not PNG. Fix: (1) detect actual format by magic bytes / `PIL.Image.identify`; (2) save with correct extension; (3) render SVG→PNG via `cairosvg` before vision submission; (4) always `PIL.Image.verify()` before submitting any file to LLM vision. | Added image-validation agentic principle to `copilot-instructions.md`; added Recraft format table + validation workflow step to `art-pipeline/references.md`; REC-6 marked DONE; AD-7 added to RS-3 | copilot-instructions.md, art-pipeline/references.md, RS-3_AI-GeneratedArtAssets.md |
| 2026-04-16 | RS-3 N-7 Scene Regeneration | Generated throne room + corridor as flat vector SVGs via Recraft. Key discoveries: (1) Recraft REST API has no image-reference parameter — style anchor must be fully encoded in prompt text; (2) Recraft V4 Vector is 1024×1024 square-only. Script `n7_scene_regen.py` implements magic-byte format detection, auto SVG→PNG render, PIL.verify, prompt-log append — reusable for all future Recraft scene sessions. All 4 variants passed flat vector spec; throne-room-v1 and corridor-v1 selected. | Added `n7_scene_regen.py` + probe scripts to art-pipeline/references.md generation scripts table; text-only style anchor note added; prompt-log.md cleaned (removed stale stubs + duplicate stalled-session entries); AD-8 + N-7 findings recorded in RS-3 | art-pipeline/references.md, RS-3_AI-GeneratedArtAssets.md, prompt-log.md |
| 2026-04-17 | API Docs Retrieval Skill ExecPlan (exec-plan-api-docs-skill.md) | New `api-docs` skill created and wired into governance. Key findings: (1) chub CLI v0.1.3 installed; Windows `mkdir ''` path bug discovered and locally patched (`lastIndexOf('/')` → `dirname()`); (2) `chub search <query>` only searches 20 bundled entries — agents must use `chub get <known-id>` from confirmed ID table; (3) 8 Python dep IDs confirmed; 12 Android/Kotlin fallback URLs verified; (4) Decision D-1: chub-primary with URL fallback. | Created `.github/skills/api-docs/SKILL.md` (88 lines) + `references.md` (100 lines); wired into `copilot-instructions.md`, `compound-engineering/SKILL.md` detection checklist, `governance.md` artifact manifest; Windows bug + chub search limitation documented in api-docs/references.md Skill Failure Log | api-docs/SKILL.md, api-docs/references.md, copilot-instructions.md, compound-engineering/SKILL.md, governance.md |
| 2026-04-17 | RS-6 Nano Banana sessions (sessionlog.txt + FollowUpSessionLog.txt compound retrace) | **Image format mismatch loop recurred for the 3rd time** — Nano Banana API returned JPEG saved as .png, agent loops failed to submit to vision. Follow-up retrace session also struggled. Root cause: `_image_utils.py` was RS-6-scoped, not shared; RS-3 n5 still had no format detection. **Fix:** (1) Promoted `_image_utils.py` to `tools/shared/retrieve_image.py` with full pipeline (magic bytes + PIL.verify + SVG→PNG + JPEG/WebP→PNG conversion); (2) Created `.github/instructions/safe-image-retrieval.instructions.md` to enforce use; (3) Patched RS-3 n5_recraft_eval.py and RS-6 _image_utils.py to delegate to shared utility. Also discovered: session memory (`/memories/session/`) is ephemeral — Q&A captured there is lost when session ends. Must use durable storage for cross-session findings. | Created `tools/shared/retrieve_image.py` + `tools/shared/__init__.py`; created `.github/instructions/safe-image-retrieval.instructions.md`; updated RS-7 `_image_utils.py` to delegate; patched RS-3 `n5_recraft_eval.py`; updated exec-plan-rs7.md with accurate status; updated compound-engineering references Q&A Log | tools/shared/retrieve_image.py, safe-image-retrieval.instructions.md, tools/rs7/_image_utils.py, tools/rs3/n5_recraft_eval.py, exec-plan-rs7.md, this file |

## Session Q&A Log

Captures clarifying questions and steering corrections from sessions. Recurring patterns become
upfront questions in future ExecPlan creation.

| Date | ExecPlan / Session | Question or Correction | Source | Candidate Upfront Question |
|------|--------------------|----------------------|--------|---------------------------|
| 2026-04-15 | RS-5 Evaluation ExecPlan | Were ground truth files verified before evaluation started? | Agent discovered GT errors during Stage 1 execution (throne-room v1 had no doors; corridor had 5 wrong doors) | Before running evaluation: verify all ground truth files against the input image/text by manual inspection |
| 2026-04-15 | RS-5 Evaluation ExecPlan | Were all `prompt_variation` types end-to-end implemented in the runner? | Agent assumed `two-pass` was implemented in `run_trial()` — it was only in `_build_prompt()`. Bug found and fixed before Stage 2a ran. | Before running evaluation: verify every `prompt_variation` value in the config has a corresponding code path in `run_trial()`, not just `_build_prompt()` |
| 2026-04-16 | RS-5 Post-Evaluation Analysis | Are scene exits visually explicit (door frames) or implied (path gaps)? | Discovered mid-analysis — outdoor-carriage exits are path gaps with no door frame. All models except Claude scored 0 door detection on image input. The scene type determines whether door detection is even a fair model task. | Before designing evaluation scenes: classify each scene's exit type (explicit / implied / topology-fixed). Score door detection only where exits are visually explicit. |
| 2026-04-16 | RS-5 Post-Evaluation Analysis | Whose responsibility is door placement — model or developer? | User steering correction: developer defines the nav graph before the pipeline runs. Model should fill zones + spawns; door positions should be pre-seeded. This reframes the entire pipeline scope. | Before any scene template pipeline ExecPlan: ask upfront — are door positions author-defined (nav graph) or model-inferred (from image/text)? The answer determines pipeline architecture. |
| 2026-04-16 | RS-3 N-5 Recraft evaluation | Agent saved all Recraft outputs as `.png` regardless of actual format (SVG/WebP). When it tried to submit them to vision analysis, the API rejected the files. The agent retried the same submissions in a loop without diagnosing root cause. Session had to be recovered manually. | Validate file format before vision submission (magic bytes + `PIL.Image.verify()`). Render SVG→PNG if needed. Never assume file extension matches content. | Before any session that downloads files from an external image API: (a) verify actual file format by content inspection, not extension; (b) if submitting to LLM vision, confirm format is JPEG/PNG/WebP/GIF before attempting || 2026-04-16 | RS-3 N-7 Scene Regeneration | Agent assumed Recraft supports landscape sizes and that the API accepts image-reference style anchors (same as Midjourney `--sref`). Both assumptions were wrong — required probe scripts to discover. 1024×1024 only; text-only prompt. | Before any Recraft generation session: (a) confirm target size is 1024×1024 (or probe if uncertain); (b) encode style anchor characteristics in text — no image-ref parameter exists |
| 2026-04-17 | API Docs Skill ExecPlan | `chub get <id> --lang py` failed with `ENOENT: mkdir ''` on Windows. Root cause: `cache.js` used `cachedPath.lastIndexOf('/')` which returns -1 on Windows backslash paths. Patched locally; fix is in upstream PR but not released to npm. | Before any session using chub on Windows: run `chub get pillow/package --lang py` as a probe; if it fails with `ENOENT mkdir`, apply `dirname()` patch to `cache.js` line ~188 |
| 2026-04-17 | API Docs Skill ExecPlan | `chub search <query>` returned 0 results for known packages (anthropic, openai). The BM25 index only covers the 20-entry bundled local registry, not the CDN catalog of ~300 entries. Agents cannot discover IDs by search. | Before using chub search to find an ID: use the confirmed ID table in `api-docs/references.md` instead. If ID is unknown, scan chub's bundled registry at `node_modules/@aisuite/chub/dist/docs/` |
| 2026-04-17 | RS-6 session 1 (sessionlog.txt) | Agent saved Nano Banana API responses as .png files despite API returning JPEG. Then submitted these mislabelled files to vision analysis, which silently failed. Agent retried the same failed submissions in a loop (~10+ attempts) without ever diagnosing the root cause (format mismatch). This is the THIRD occurrence of this exact pattern (RS-3 N-5, RS-6 N-3). | **PROMOTED TO INSTRUCTION:** `.github/instructions/safe-image-retrieval.instructions.md` now enforces `tools/shared/retrieve_image.py` for ALL image downloads. This pattern has recurred 3 times — sufficient evidence for a mandatory instruction, not just a copilot-instructions suggestion. |
| 2026-04-17 | RS-6 session 1 (sessionlog.txt) | User asked "what is `NB_STYLE_ANCHOR_URL` for?" — agent had set up the env var without explaining its purpose. Then user asked "why was v4 chosen over v3?" — no rationale was recorded for canonical style selection. | Before introducing new env vars: explain what they do and why. When recording design decisions (canonical style selection, model choice), always record the rationale — not just the outcome. |
| 2026-04-17 | RS-6 follow-up session (FollowUpSessionLog.txt) | Follow-up agent was asked to retrace session 1 and continue. Despite detailed instructions to "do a more cautious step" with images, the agent still needed to discover the format mismatch independently by running magic-byte checks. The per-script `_image_utils.py` fix was local to rs6/ and not discoverable by other spikes. | Before any image-downloading session: check if `tools/shared/retrieve_image.py` exists and `from shared.retrieve_image import download_image`. This is now a mandatory import for all tools/ scripts (see safe-image-retrieval instruction). |
| 2026-04-17 | RS-6 compound retrace | Session memory (`/memories/session/qa-capture.md`) is ephemeral — cleared when the VS Code session ends. The compound-engineering skill tells agents to write Q&A there, but a follow-up session cannot access it. The data is lost. | When Q&A findings are significant enough to survive the session: write them to `/memories/repo/` (durable repository memory) instead of `/memories/session/`. Session memory is for within-session scratch notes only. |
### How to Use This Log

**When creating an ExecPlan:** Scan the Q&A Log for patterns relevant to the planned work.
If the same type of question has been asked ≥2 times, it SHOULD be asked upfront as a precondition.

**Categories of upfront questions to look for:**
- **Scope:** What's included/excluded? Which archetypes/scenes/modules?
- **Implementation approach:** Runtime vs offline? Kotlin vs Python? Test vs standalone tool?
- **File handling:** Overwrite vs copy? Output directory structure?
- **Acceptance criteria:** How will "done" be verified? What quality bar applies?
- **Dependencies:** What must exist before this work can start?
- **Trade-offs:** Are there known alternatives? What's the deciding factor?

## Session Log Accessibility — Technical Limitations

**Can an agent review session logs?** No — not retrospectively.

| Capability | Available? | Notes |
|-----------|-----------|-------|
| Read full session transcript | **No** | No tool or file provides the conversation history |
| Read VS Code debug logs | **No** | `VSCODE_TARGET_SESSION_LOG` path doesn't materialise as a readable file |
| Review own tool calls (current session) | **Yes** | Agent retains in-context memory of its actions in the current turn |
| Review Q&A from ask-questions tool | **Yes** | Agent sees tool call results in its current context |
| Read session memory files | **Yes** | `/memories/session/*.md` — readable during the session |
| Read sub-agent results | **Partial** | Large outputs are written to temp files; readable via `read_file` |

**Practical approach:** Capture Q&A **at the point of occurrence**, not retrospectively:
1. During the session, the agent writes observations to `/memories/session/qa-capture.md`
2. User steering corrections are captured when the agent processes the redirecting message
3. At compound step time, the agent harvests from session memory + its own in-context recollection
4. The compound step MUST be invoked before the session ends (session memory is cleared after)
