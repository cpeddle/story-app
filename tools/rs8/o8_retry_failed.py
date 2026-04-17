"""
RS-8 O-8 Retry — 4 Failed Trees
=================================
Retries the 4 trees that failed O-8 run 1 with strengthened prompts.

Failures from run 1:
  01 throneroom_knight_princess_brave  → gate 5 (no MOOD_NEGATIVE), gate 4 on retry (depth >3)
  03 throneroom_knight_princess_shy    → gate 6 (SHY used as tone value)
  08 throneroom_knight_dragon_kind     → gate 5 (no MOOD_NEGATIVE) × 2 attempts
  14 courtyard_princess_dragon_kind    → gate 5 (no MOOD_NEGATIVE) × 2 attempts

Changes vs o8_bulk_corpus.py:
  - EN_SYSTEM: stronger MOOD_NEGATIVE requirement, explicit SHY-is-not-a-tone warning,
    explicit max-depth-3 constraint
  - Individual prompts: each one now explicitly names the required negative branch
  - MAX_RETRIES: 3 (one more than run 1)

Usage:
    cd tools
    uv run --with python-dotenv python rs8/o8_retry_failed.py
"""

from __future__ import annotations

import json
import math
import os
import re
import sys
import time
from collections import deque
from pathlib import Path

import sys as _sys
if hasattr(_sys.stdout, 'reconfigure'):
    _sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    _sys.stderr.reconfigure(encoding='utf-8', errors='replace')

ENV_FILE = Path(__file__).parent.parent / ".env"
if ENV_FILE.exists():
    from dotenv import load_dotenv
    load_dotenv(ENV_FILE)

import openai

ASSETS_DIALOGUE = Path(__file__).parent.parent.parent / "assets" / "dialogue"
ASSETS_DIALOGUE.mkdir(parents=True, exist_ok=True)

OUT_DIR = Path(__file__).parent / "outputs" / "o8"
OUT_DIR.mkdir(parents=True, exist_ok=True)

PROMPT_LOG = Path(__file__).parent.parent.parent / "assets" / "prompt-log.md"
CATALOGUE   = ASSETS_DIALOGUE / "catalogue.json"

GENERATION_MODEL  = "gpt-4.1-mini"
TRANSLATION_MODEL = "gpt-4.1-mini"

PRICING = {"input": 0.40, "output": 1.60}  # USD per million tokens

MAX_RETRIES = 3  # one more than run 1


# ---------------------------------------------------------------------------
# Retry corpus — only the 4 failed trees with strengthened prompts
# ---------------------------------------------------------------------------

CORPUS: list[dict] = [
    {
        "treeId":    "throneroom_knight_princess_brave_001",
        "scenarioId": "throneroom_brave_story",
        "scene":     "castle_throne_room",
        "pair":      "knight_princess",
        "traitId":   "BRAVE",
        "setting":   "Castle throne room",
        "prompt":    (
            "The Knight is feeling BRAVE today. He wants to impress the Princess by telling her "
            "a slightly scary story about his adventure in the forest. Knight is speaker.\n\n"
            "REQUIRED NEGATIVE BRANCH: Include a path where Princess gets frightened by the story "
            "and tells Knight to stop — this path MUST end with outcome MOOD_NEGATIVE.\n"
            "TREE DEPTH: Maximum 3 levels from root. Do NOT go deeper than level 3."
        ),
    },
    {
        "treeId":    "throneroom_knight_princess_shy_001",
        "scenarioId": "throneroom_shy_help",
        "scene":     "castle_throne_room",
        "pair":      "knight_princess",
        "traitId":   "SHY",
        "setting":   "Castle throne room",
        "prompt":    (
            "The Princess is SHY. She needs help carrying a heavy book from the high shelf, "
            "but she is too shy to ask the Knight directly. She eventually works up the courage "
            "to ask. Princess is speaker.\n\n"
            "TONE RULE: The 'tone' field for every node MUST be FRIENDLY, NEUTRAL, or GRUMPY. "
            "SHY is the character trait — it is NEVER a valid tone value. A shy character speaks "
            "with FRIENDLY or NEUTRAL tone.\n"
            "REQUIRED NEGATIVE BRANCH: Include a path where Knight misunderstands her and leaves "
            "— this MUST end with outcome MOOD_NEGATIVE."
        ),
    },
    {
        "treeId":    "throneroom_knight_dragon_kind_001",
        "scenarioId": "throneroom_kind_snack",
        "scene":     "castle_throne_room",
        "pair":      "knight_dragon",
        "traitId":   "KIND",
        "setting":   "Castle throne room",
        "prompt":    (
            "The Knight is KIND. He has brought Dragon a big bowl of shiny red apples as a surprise gift. "
            "Knight presents the gift. Knight is speaker.\n\n"
            "REQUIRED NEGATIVE BRANCH: Include a path where Dragon already has too many apples and "
            "grumpily rejects the gift — this MUST end with outcome MOOD_NEGATIVE. "
            "A kind gesture can still be misunderstood or unwanted.\n"
            "TREE DEPTH: Maximum 3 levels from root."
        ),
    },
    {
        "treeId":    "courtyard_princess_dragon_kind_001",
        "scenarioId": "courtyard_kind_flowers",
        "scene":     "castle_courtyard",
        "pair":      "princess_dragon",
        "traitId":   "KIND",
        "setting":   "Castle courtyard (gardens, bright day)",
        "prompt":    (
            "The Princess is KIND. She and Dragon are picking flowers in the courtyard garden. "
            "Princess wants to share her favourite flowers with Dragon. Princess is speaker.\n\n"
            "REQUIRED NEGATIVE BRANCH: Include a path where Dragon accidentally sneezes on all "
            "the flowers and destroys them, making Princess upset — this MUST end with "
            "outcome MOOD_NEGATIVE. Kind moments can still go wrong.\n"
            "TREE DEPTH: Maximum 3 levels from root."
        ),
    },
]


# ---------------------------------------------------------------------------
# System prompt — reinforced over run 1
# ---------------------------------------------------------------------------

EN_SYSTEM = """You are a bilingual dialogue writer for a children's fantasy play app.
Target audience: 7-year-old children. Language register: warm, simple, encouraging.

OUTPUT FORMAT: Respond with a single valid JSON object. No markdown fences, no commentary.

The JSON must match this exact schema:
{
  "treeId": string,
  "scenarioId": string,
  "traitId": "BRAVE|SHY|KIND|SILLY|GRUMPY|CURIOUS",
  "rootNodeId": "node_0",
  "nodes": [
    {
      "nodeId": "node_0",
      "speaker": "character",
      "characterLine": { "en": "..." },
      "tone": "FRIENDLY|NEUTRAL|GRUMPY",
      "branches": [
        { "branchId": "br_0_1", "playerLabel": { "en": "..." }, "targetNodeId": "node_1" }
      ]
    }
  ]
}

STRUCTURAL RULES (ALL MANDATORY):
1. Root node (node_0) MUST have AT LEAST 3 branches.
2. Every non-leaf node MUST have 2–4 branches.
3. Minimum tree depth: 2 levels. MAXIMUM depth: 3 levels — level 4 is INVALID.
4. Every leaf node (branches = []) MUST have "outcome": "MOOD_POSITIVE"|"MOOD_NEGATIVE"|"NEUTRAL".
5. Non-leaf nodes MUST NOT have an "outcome" field.
6. Every "targetNodeId" MUST reference an existing "nodeId" in the nodes array.
7. No unreachable nodes (every node except node_0 must be reachable from node_0).
8. "tone" must be FRIENDLY, NEUTRAL, or GRUMPY ONLY — these are the ONLY valid values.
9. *** CRITICAL *** Every tree MUST have AT LEAST ONE MOOD_NEGATIVE leaf outcome.
   Stories where nothing ever goes wrong are NOT accepted.
10. All text must be appropriate for a 7-year-old: short sentences, simple words.
11. Language: EN only in characterLine.en and playerLabel.en fields.

⚠ TONE WARNING: The "tone" field is NEVER the same as the character's traitId.
   Valid tones: FRIENDLY, NEUTRAL, GRUMPY.
   INVALID tone values: SHY, BRAVE, KIND, SILLY, CURIOUS — these are traits, NOT tones.
   A SHY character speaks with tone FRIENDLY or NEUTRAL.
   A BRAVE character speaks with tone FRIENDLY or NEUTRAL.

⚠ DEPTH WARNING: Maximum depth is 3 levels. If node_0 has branches to level-1 nodes,
   level-1 nodes have branches to level-2 nodes, level-2 nodes may have branches to
   level-3 nodes, but level-3 nodes MUST be leaves (no further branches).

⚠ MOOD_NEGATIVE WARNING: You MUST include at least one path that ends MOOD_NEGATIVE.
   The story prompt tells you exactly which situation leads to the negative outcome.
   Do not ignore it.

STYLE: Fantasy castle setting. Characters: Princess, Knight, Dragon.
Keep all lines short (max 15 words). Player choices very brief (max 6 words)."""


NL_SYSTEM = """You are a bilingual Dutch/English translator for children's dialogue (ages 5–8).

Add "nl" translations to the JSON dialogue tree. RULES:
1. Add "nl" key to every characterLine AND every playerLabel.
2. Dutch must be idiomatic and natural — NOT word-for-word translation.
3. Register: informal, warm, child-level ('jij/jou', NEVER 'u').
4. Keep all punctuation and rhythm similar.
5. Do NOT change any other fields.
6. Return the complete JSON with added nl fields. No markdown fences, no commentary."""


# ---------------------------------------------------------------------------
# Gate validators (identical to o8_bulk_corpus.py)
# ---------------------------------------------------------------------------

VALID_TONES    = {"FRIENDLY", "NEUTRAL", "GRUMPY"}
VALID_OUTCOMES = {"MOOD_POSITIVE", "MOOD_NEGATIVE", "NEUTRAL"}

def _gate1(tree):
    req = {"treeId","scenarioId","traitId","rootNodeId","nodes"}
    miss = req - set(tree.keys())
    if miss: return False, f"missing tree fields: {miss}"
    if not isinstance(tree.get("nodes"), list) or not tree["nodes"]:
        return False, "nodes must be non-empty list"
    issues = []
    for n in tree["nodes"]:
        m = {"nodeId","speaker","characterLine","tone","branches"} - set(n.keys())
        if m: issues.append(f"{n.get('nodeId','?')}: missing {m}")
        if "en" not in n.get("characterLine", {}):
            issues.append(f"{n.get('nodeId','?')}: characterLine.en missing")
    return (False, "; ".join(issues[:2])) if issues else (True, "ok")

def _gate2(tree):
    nids = {n["nodeId"] for n in tree["nodes"]}
    root = tree.get("rootNodeId","node_0")
    bad  = [f"{n['nodeId']}->{b['targetNodeId']}" for n in tree["nodes"]
            for b in n.get("branches",[]) if b.get("targetNodeId") not in nids]
    if bad: return False, f"dangling refs: {bad[:2]}"
    reach, q = set(), deque([root])
    nmap = {n["nodeId"]: n for n in tree["nodes"]}
    while q:
        nid = q.popleft()
        if nid in reach: continue
        reach.add(nid); nd = nmap.get(nid)
        if nd:
            for b in nd.get("branches",[]): q.append(b["targetNodeId"])
    unreach = nids - reach
    return (False, f"unreachable: {unreach}") if unreach else (True, f"ok ({len(nids)} nodes)")

def _gate3(tree):
    root = tree.get("rootNodeId","node_0"); issues = []
    for n in tree["nodes"]:
        b = len(n.get("branches",[]));
        if b == 0: continue
        if n["nodeId"] == root:
            if b < 3: issues.append(f"root has {b} branches (need ≥3)")
        elif not (2 <= b <= 4):
            issues.append(f"{n['nodeId']} has {b} branches")
    return (False, "; ".join(issues)) if issues else (True, "ok")

def _gate4(tree):
    root = tree.get("rootNodeId","node_0")
    nmap = {n["nodeId"]: n for n in tree["nodes"]}
    depths, q = {}, deque([(root, 0)])
    while q:
        nid, d = q.popleft()
        if nid in depths: continue
        depths[nid] = d; nd = nmap.get(nid)
        if nd:
            for b in nd.get("branches",[]): q.append((b["targetNodeId"], d+1))
    mx = max(depths.values()) if depths else 0
    if mx < 2: return False, f"max depth {mx} < 2"
    if mx > 3: return False, f"max depth {mx} > 3"
    return True, f"ok (depth {mx})"

def _gate5(tree):
    issues = []
    for n in tree["nodes"]:
        leaf = len(n.get("branches",[])) == 0; out = n.get("outcome")
        if leaf and out not in VALID_OUTCOMES: issues.append(f"{n['nodeId']} bad outcome {out!r}")
        if not leaf and out is not None: issues.append(f"{n['nodeId']} non-leaf has outcome")
    if issues: return False, "; ".join(issues[:2])
    outs = [n.get("outcome") for n in tree["nodes"] if len(n.get("branches",[])) == 0]
    if "MOOD_POSITIVE" not in outs: return False, "no MOOD_POSITIVE leaf"
    if "MOOD_NEGATIVE" not in outs: return False, "no MOOD_NEGATIVE leaf"
    return True, f"ok {sorted(set(outs))}"

def _gate6(tree):
    bad = [f"{n['nodeId']}:{n.get('tone')!r}" for n in tree["nodes"] if n.get("tone") not in VALID_TONES]
    return (False, f"bad tones: {bad[:2]}") if bad else (True, "ok")

def _count_syl(w):
    w=w.lower().strip(".,!?\"'"); v="aeiouy"; c=0; iv=False
    for ch in w:
        if ch in v:
            if not iv: c+=1; iv=True
        else: iv=False
    if w.endswith("e") and c>1: c-=1
    return max(1,c)

def _gate7(tree):
    texts=[n.get("characterLine",{}).get("en","") for n in tree["nodes"]]
    texts+=[b.get("playerLabel",{}).get("en","") for n in tree["nodes"] for b in n.get("branches",[])]
    combined=" ".join(t for t in texts if t)
    sents=re.split(r'[.!?]+', combined); sents=[s.strip() for s in sents if s.strip()]
    words=re.findall(r"\b[a-zA-Z']+\b", combined)
    if not words or not sents: return True, "ok (insufficient text)"
    grade=0.39*(len(words)/len(sents))+11.8*(sum(_count_syl(w) for w in words)/len(words))-15.59
    return (False, f"FK grade {grade:.1f} > 2.5") if grade > 2.5 else (True, f"ok (FK ≈{grade:.1f})")

def _gate8(client, tree):
    texts = ([n.get("characterLine",{}).get("en","") for n in tree["nodes"]]
             + [b.get("playerLabel",{}).get("en","") for n in tree["nodes"] for b in n.get("branches",[])])
    flagged = []
    for t in texts:
        if not t: continue
        try:
            r = client.moderations.create(input=t, model="omni-moderation-latest")
            if r.results[0].flagged:
                cats = [k for k,v in vars(r.results[0].categories).items() if v]
                flagged.append(f"'{t[:30]}': {cats}")
        except Exception as e:
            flagged.append(f"moderation_error: {e}")
    return (False, f"flagged: {flagged[:1]}") if flagged else (True, f"ok ({len(texts)} strings)")

def run_gates(client, tree):
    results = {}
    for name, fn in [
        ("1_schema",   lambda t: _gate1(t)),
        ("2_graph",    lambda t: _gate2(t)),
        ("3_branches", lambda t: _gate3(t)),
        ("4_depth",    lambda t: _gate4(t)),
        ("5_outcomes", lambda t: _gate5(t)),
        ("6_tone",     lambda t: _gate6(t)),
        ("7_vocab",    lambda t: _gate7(t)),
        ("8_content",  lambda t: _gate8(client, t)),
    ]:
        try: p, d = fn(tree)
        except Exception as e: p, d = False, f"exception: {e}"
        results[name] = {"pass": p, "detail": d}
    results["overall"] = all(v["pass"] for v in results.values())
    return results


# ---------------------------------------------------------------------------
# Generation helpers
# ---------------------------------------------------------------------------

def cal_cost(in_t, out_t):
    return (in_t / 1_000_000) * PRICING["input"] + (out_t / 1_000_000) * PRICING["output"]

def generate_en(client, entry: dict, temperature=0.7) -> tuple[dict | None, dict]:
    user_msg = (
        f"Setting: {entry['setting']}.\n"
        f"Character pair: {entry['pair'].replace('_', ' & ')}.\n"
        f"TraitId: {entry['traitId']}\n"
        f"TreeId: {entry['treeId']}\nScenarioId: {entry['scenarioId']}\n\n"
        f"{entry['prompt']}"
    )
    t0 = time.perf_counter()
    try:
        r = client.chat.completions.create(
            model=GENERATION_MODEL,
            messages=[{"role":"system","content":EN_SYSTEM}, {"role":"user","content":user_msg}],
            response_format={"type":"json_object"},
            temperature=temperature, max_tokens=2000,
        )
        ms = round((time.perf_counter()-t0)*1000)
        raw = r.choices[0].message.content or ""
        u = r.usage; it = u.prompt_tokens if u else 0; ot = u.completion_tokens if u else 0
        try: tree = json.loads(raw)
        except json.JSONDecodeError as e:
            return None, {"ms": ms, "in": it, "out": ot, "cost": cal_cost(it,ot), "err": str(e)}
        return tree, {"ms": ms, "in": it, "out": ot, "cost": cal_cost(it,ot), "err": None}
    except Exception as e:
        return None, {"ms": round((time.perf_counter()-t0)*1000), "in":0,"out":0,"cost":0,"err":str(e)}

def translate_nl(client, tree: dict, temperature=0.3) -> tuple[dict | None, dict]:
    t0 = time.perf_counter()
    try:
        r = client.chat.completions.create(
            model=TRANSLATION_MODEL,
            messages=[
                {"role":"system","content":NL_SYSTEM},
                {"role":"user","content":json.dumps(tree, ensure_ascii=False)},
            ],
            response_format={"type":"json_object"},
            temperature=temperature, max_tokens=3000,
        )
        ms = round((time.perf_counter()-t0)*1000)
        raw = r.choices[0].message.content or ""
        u = r.usage; it = u.prompt_tokens if u else 0; ot = u.completion_tokens if u else 0
        try: translated = json.loads(raw)
        except json.JSONDecodeError as e:
            return None, {"ms": ms, "in": it, "out": ot, "cost": cal_cost(it,ot), "err": str(e)}
        return translated, {"ms": ms, "in": it, "out": ot, "cost": cal_cost(it,ot), "err": None}
    except Exception as e:
        return None, {"ms": round((time.perf_counter()-t0)*1000), "in":0,"out":0,"cost":0,"err":str(e)}


def _out_path(entry: dict) -> Path:
    scene = entry["scene"]
    pair  = entry["pair"]
    trait = entry["traitId"].lower()
    return ASSETS_DIALOGUE / f"{scene}_{pair}_{trait}.json"


def _load_catalogue() -> list:
    if CATALOGUE.exists():
        return json.loads(CATALOGUE.read_text(encoding="utf-8"))
    return []


def _save_catalogue(entries: list) -> None:
    CATALOGUE.write_text(
        json.dumps(entries, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    api_key = os.environ.get("OPENAI_API_KEY","").strip().strip('"').strip("'")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not set.", file=sys.stderr); sys.exit(1)
    client = openai.OpenAI(api_key=api_key)

    total_cost = 0.0
    gate_failures = 0
    newly_saved: list[dict] = []

    print(f"O-8 Retry — {len(CORPUS)} trees (improved prompts)")
    print(f"Model: {GENERATION_MODEL} | MAX_RETRIES: {MAX_RETRIES}")
    print("="*60)

    for i, entry in enumerate(CORPUS, 1):
        tid = entry["treeId"]
        out_path = _out_path(entry)
        print(f"\n[{i:02d}/{len(CORPUS)}] {tid}")

        # Skip if already exists from a previous retry run
        if out_path.exists():
            print(f"  ⏭ Already exists — skipping")
            continue

        # --- Pass 1: EN generation with retry ---
        en_tree = None
        gates = {}
        for attempt in range(1, MAX_RETRIES + 1):
            temp = 0.7 + (attempt - 1) * 0.15   # 0.70 → 0.85 → 1.00
            print(f"  EN gen (attempt {attempt}, T={temp:.2f})...", end="", flush=True)
            en_tree, gen_meta = generate_en(client, entry, temperature=temp)
            total_cost += gen_meta.get("cost", 0.0)

            if en_tree is None:
                print(f" ❌ PARSE ERROR: {gen_meta.get('err')}")
                if attempt == MAX_RETRIES:
                    break
                continue

            print(f" ✅ {gen_meta['ms']}ms ${gen_meta['cost']:.5f}")
            gates = run_gates(client, en_tree)

            if gates["overall"]:
                gate_sym = " ".join("✅" if v["pass"] else "❌"
                                    for k, v in gates.items() if k != "overall")
                print(f"  Gates: {gate_sym}")
                break
            else:
                fails = [f"{k}: {v['detail']}" for k, v in gates.items()
                         if k != "overall" and not v["pass"]]
                print(f"  Gates: ❌ FAIL: {' | '.join(fails)}")
                if attempt < MAX_RETRIES:
                    print(f"  → retry {attempt + 1}")
                    en_tree = None

        if en_tree is None or not gates.get("overall"):
            print(f"  ❌ STILL FAILED after {MAX_RETRIES} attempts")
            gate_failures += 1
            continue

        # --- Pass 2: NL translation ---
        print(f"  NL trans...", end="", flush=True)
        nl_tree, nl_meta = translate_nl(client, en_tree)
        total_cost += nl_meta.get("cost", 0.0)

        if nl_tree is None:
            print(f" ❌ NL PARSE ERROR: {nl_meta.get('err')} — saving EN-only")
            nl_tree = en_tree

        print(f" ✅ {nl_meta['ms']}ms ${nl_meta['cost']:.5f}")

        # Save
        out_path.write_text(json.dumps(nl_tree, indent=2, ensure_ascii=False), encoding="utf-8")
        scene_label = entry["scene"].replace("_", " ").title()
        print(f"  Saved → {out_path.relative_to(Path(__file__).parent.parent.parent)}")

        newly_saved.append({
            "treeId":     entry["treeId"],
            "scenarioId": entry["scenarioId"],
            "scene":      entry["scene"],
            "pair":       entry["pair"],
            "traitId":    entry["traitId"],
            "file":       out_path.name,
        })

    # --- Update catalogue ---
    if newly_saved:
        catalogue = _load_catalogue()
        existing_ids = {e["treeId"] for e in catalogue}
        for item in newly_saved:
            if item["treeId"] not in existing_ids:
                catalogue.append(item)
        _save_catalogue(catalogue)
        print(f"\n  Catalogue updated: {len(catalogue)} total entries")

    # --- Prompt log ---
    run_date = time.strftime("%Y-%m-%d")
    log_entry = (
        f"\n## O-8 Retry — {run_date}\n"
        f"- Script: `tools/rs8/o8_retry_failed.py`\n"
        f"- Model:  {GENERATION_MODEL} (EN), {TRANSLATION_MODEL} (NL)\n"
        f"- Trees retried: {len(CORPUS)}\n"
        f"- Trees saved:   {len(newly_saved)}\n"
        f"- Still failed:  {gate_failures}\n"
        f"- Cost:          ${total_cost:.4f}\n"
    )
    try:
        existing = PROMPT_LOG.read_text(encoding="utf-8") if PROMPT_LOG.exists() else ""
        PROMPT_LOG.write_text(existing + log_entry, encoding="utf-8")
    except Exception as e:
        print(f"  (prompt-log write failed: {e})")

    # --- Summary ---
    print("\n" + "="*60)
    print("O-8 RETRY COMPLETE")
    print(f"  Trees saved:  {len(newly_saved)}/{len(CORPUS)}")
    print(f"  Still failed: {gate_failures}")
    print(f"  Total cost:   ${total_cost:.4f}")
    if gate_failures == 0:
        print("\nO-8 GATE: FULL PASS ✅ — all 18 trees generated")
    else:
        print(f"\nO-8 GATE: PARTIAL ⚠️ ({gate_failures} trees still failing)")


if __name__ == "__main__":
    main()
