# Dialogue Generation — References

Companion document to [`SKILL.md`](SKILL.md). Contains complete reference material for dialogue tree JSON validation, bilingual generation, content filtering, and quality evaluation.

> **Schema authority:** The canonical dialogue tree schema is defined in [RS-2 §5](../../docs/investigations/RS-2_DialogueTreeGeneration.md). This file documents the same schema for quick skill reference. If a discrepancy exists, RS-2 is authoritative.

## Full JSON Schema Example

The schema uses a **flat node array with explicit `targetNodeId` references** (not recursive nesting). This is optimised for LLM JSON schema constraints and Kotlinx Serialization.

```json
{
  "treeId": "playground_sharing_brave_001",
  "scenarioId": "playground_sharing",
  "traitId": "BRAVE",
  "rootNodeId": "node_0",
  "nodes": [
    {
      "nodeId": "node_0",
      "speaker": "character",
      "characterLine": { "en": "Can we share that cool robot?", "nl": "Mogen we die gave robot delen?" },
      "tone": "FRIENDLY",
      "branches": [
        {
          "branchId": "br_0_1",
          "playerLabel": { "en": "Sure! Let's play together!", "nl": "Ja! Laten we samen spelen!" },
          "targetNodeId": "node_1"
        },
        {
          "branchId": "br_0_2",
          "playerLabel": { "en": "Hmm, maybe later...", "nl": "Hmm, misschien later..." },
          "targetNodeId": "node_2"
        },
        {
          "branchId": "br_0_3",
          "playerLabel": { "en": "No way, it's mine!", "nl": "Nee, hij is van mij!" },
          "targetNodeId": "node_3"
        }
      ]
    },
    {
      "nodeId": "node_1",
      "speaker": "character",
      "characterLine": { "en": "Great! What shall we build?", "nl": "Leuk! Wat zullen we bouwen?" },
      "tone": "FRIENDLY",
      "branches": [],
      "outcome": "MOOD_POSITIVE"
    },
    {
      "nodeId": "node_2",
      "speaker": "character",
      "characterLine": { "en": "Okay, I'll show you my trick first!", "nl": "Oké, ik laat eerst mijn truc zien!" },
      "tone": "NEUTRAL",
      "branches": [
        {
          "branchId": "br_2_1",
          "playerLabel": { "en": "Wow, that's cool!", "nl": "Wauw, dat is cool!" },
          "targetNodeId": "node_4"
        },
        {
          "branchId": "br_2_2",
          "playerLabel": { "en": "I don't care.", "nl": "Maakt me niet uit." },
          "targetNodeId": "node_5"
        }
      ]
    },
    {
      "nodeId": "node_3",
      "speaker": "character",
      "characterLine": { "en": "Oh... okay then.", "nl": "Oh... oké dan." },
      "tone": "GRUMPY",
      "branches": [],
      "outcome": "MOOD_NEGATIVE"
    },
    {
      "nodeId": "node_4",
      "speaker": "character",
      "characterLine": { "en": "Let's play more!", "nl": "Laten we meer spelen!" },
      "tone": "FRIENDLY",
      "branches": [],
      "outcome": "MOOD_POSITIVE"
    },
    {
      "nodeId": "node_5",
      "speaker": "character",
      "characterLine": { "en": "Fine, I'll play alone.", "nl": "Goed, ik speel alleen." },
      "tone": "NEUTRAL",
      "branches": [],
      "outcome": "NEUTRAL"
    }
  ]
}
```

## Kotlin Data Class Definitions

Use Kotlinx Serialization (TD-11) — NOT Gson or Moshi.

```kotlin
@Serializable
data class DialogueTree(
    val treeId: String,
    val scenarioId: String,
    val traitId: TraitId,
    val rootNodeId: String,
    val nodes: List<DialogueNode>,
)

@Serializable
data class DialogueNode(
    val nodeId: String,
    val speaker: String,              // "character" or character ID
    val characterLine: LocalisedString,
    val tone: Tone,
    val branches: List<DialogueBranch>,
    val outcome: DialogueOutcome? = null,
)

@Serializable
data class DialogueBranch(
    val branchId: String,
    val playerLabel: LocalisedString,
    val targetNodeId: String,
)

@Serializable
data class LocalisedString(
    val en: String,
    val nl: String? = null,
)

@Serializable
enum class Tone { FRIENDLY, NEUTRAL, GRUMPY }

@Serializable
enum class TraitId { BRAVE, SHY, KIND, SILLY, GRUMPY, CURIOUS }

@Serializable
enum class DialogueOutcome { MOOD_POSITIVE, MOOD_NEGATIVE, NEUTRAL }
```

**Invariants:**
- `branches` is empty on leaf nodes; `outcome` is null on non-leaf nodes
- Every path from root to leaf MUST terminate with a non-null `outcome`
- `tone` is required on every node — drives mood-tone alignment evaluation
- `speaker` distinguishes character dialogue from player choices (branches have `playerLabel` instead)

## Schema Key Design Decisions

| Decision | Rationale |
|---|---|
| Flat node array (not recursive nesting) | LLM JSON schema constraints work better with flat arrays. Easier to validate graph integrity. Better for Kotlinx Serialization. |
| `targetNodeId` references (not parent-child) | Enables cycle detection, orphan detection, and graph validation. More robust for LLM-generated output. |
| `LocalisedString` (EN + NL together) | Both languages in one tree file. Avoids separate EN/NL trees drifting apart. |
| `tone` on every node | Required for tone-text alignment evaluation (soft gate). Validates that character voice matches declared mood. |
| `outcome` on leaf nodes only | Mood outcome happens when conversation ends, not per-choice. Simpler model, aligns with 3-state Mood Ladder. (Resolved: RS-2 OQ-1) |

## Outcome Value Semantics

- **MOOD_POSITIVE** — moves mood one step toward Friendly on the Mood Ladder
- **MOOD_NEGATIVE** — moves mood one step toward Grumpy on the Mood Ladder
- **NEUTRAL** — no mood change

## Bilingual Workflow

### Step 1: Generate EN Dialogue Tree

- Primary language first
- Vocabulary: age-appropriate for 7-year-old (≤Grade 2.5 reading level)
- Simple sentence structures — subject-verb-object preferred
- No idioms, slang, or cultural references that don't translate well

### Step 2: Generate NL Variant

- MUST be **idiomatic Dutch**, not literal translation from English
- Flesch-Douma readability score ≥70 (easy reading level)
- Use familiar Dutch children's vocabulary
- Respect Dutch sentence structure (verb-second in main clauses)
- Adapt character voice and dialogue flow to Dutch conversational norms

### Step 3: Validate Both Independently

- Each tree (EN and NL) must pass all hard gates independently
- Different readability/grade levels apply per locale

### Step 4: Verify Tone Consistency

- Same tone markers across EN and NL nodes
- Character personalities consistent between locales
- Emotional arc of dialogue preserved

## Content Filtering Detail (TD-13)

**Technology:** On-device TFLite model — no cloud dependency.

**Timing:** Content filter MUST run at generation time (during offline authoring phase), not at runtime.

**Filtering checks:**
- Violence or aggressive themes
- Fear-inducing or scary content
- Inappropriate sexual or adult themes
- Bullying, exclusion, or cruelty language
- Disrespect toward caregivers or authority

**Decision rule:** Any flagged content → reject and regenerate. No overrides or manual approval.

**Integration:** Call filter API after generating dialogue text, before adding node to tree.

## Evaluation Rubric — Hard Gates (All Must Pass)

| # | Gate | Criterion | Failure Action |
|---|------|-----------|----------------|
| 1 | Schema valid | JSON validates against schema constraints (types, structure) | Parse error or validation exception |
| 2 | Graph integrity | All paths from root terminate at leaf nodes; all non-leaf nodes have branches | Orphaned subtrees or dangling references |
| 3 | Min branches | Root node has ≥3 branches | Insufficient choice variety for child |
| 4 | Min depth | ≥2 levels deep on at least one path | Dialogue too shallow |
| 5 | Leaf outcomes | Every leaf has MOOD_POSITIVE, MOOD_NEGATIVE, or NEUTRAL | Unresolved outcomes; ambiguous mood impact |
| 6 | Vocabulary | ≤Grade 2.5 reading level (EN) / Flesch-Douma ≥70 (NL) | Text too complex for target age |
| 7 | Content filter | Passes on-device TFLite content safety check | Unsafe or inappropriate content detected |

**Acceptance rule:** Failure on ANY hard gate = **reject entire tree**. No partial acceptance or conditional waiving.

## Evaluation Rubric — Quality Scoring (Soft Gates)

Minimum passing score: **7.0 / 10.0** (weighted average). Used to rank dialogue trees when multiple acceptable options exist.

| Dimension | Weight | Scoring Guidance |
|-----------|--------|------------------|
| Natural dialogue flow | 25% | Does conversation feel like how a child would actually talk? Are transitions smooth? |
| Character voice consistency | 20% | Do characters sound distinct and in-character across all branches? |
| Mood outcome balance | 20% | Are branches distributed across outcomes (not all positive or all negative)? |
| Tone-text alignment | 15% | Does the text match the declared tone (friendly/neutral/grumpy)? |
| Replayability | 10% | Are branches meaningfully different, or do they lead to identical outcomes? |
| Cultural appropriateness | 10% | Suitable for both NL and EN audiences? No regional or cultural missteps? |

**Score interpretation:**
- 9–10: Exemplary — natural, engaging, well-balanced
- 7–8: Acceptable — meets requirements, minor room for polish
- 5–6: Weak — passes hard gates but fails on soft gates
- <7: Reject — does not meet quality baseline

## Open Questions (From RS-2)

These remain unresolved in design. Flag when encountered and capture findings for future iteration:

1. **Exact TFLite model selection for content filtering** — which pre-trained model? Or train custom? Latency budget on 4 GB Exynos 9611?
2. **Dialogue tree count per character pair per scene** — how many EN+NL variants needed? Combinatorial explosion risk?
3. **Tone emoji mappings** — which emoji represents friendly/neutral/grumpy? Needed for UI display?
4. **Trait influence on dialogue branches** — do character traits (e.g. "shy", "bold") directly modify available branches, or only influence generation algorithm?
5. **Edge case: both characters grumpy** — which dialogue tree is available when both characters are at Grumpy mood? Reconciliation dialogue?
6. **Fallback behaviour** — what happens when no dialogue tree matches current mood state + character pair + scene combination? Fallback generic dialogue pool?
