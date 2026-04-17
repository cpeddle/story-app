"""
RS-8 O-8 — Bulk Dialogue Corpus Generation Sprint
====================================================
Generates 18 EN+NL dialogue trees covering 2 scenes × 3 character pairs × 3 traits.
Two-pass strategy: EN generation first, then NL translation (same approach as O-3).
All 8 hard gates validated after EN generation. Content (gate 8) inline.

Usage:
    cd tools
    uv run --with python-dotenv python rs8/o8_bulk_corpus.py

Outputs:
    assets/dialogue/{scene}_{pair}_{trait}.json     — bilingual RS-2 trees
    assets/dialogue/catalogue.json                  — index of all generated trees
    tools/rs8/outputs/o8/gate_report.json           — gate + cost summary
    assets/prompt-log.md                            — updated with run record

Preconditions:
    tools/.env: OPENAI_API_KEY=sk-...
    tools/rs8/o2_dialogue_quality.py (gate validators imported from here)
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

GENERATION_MODEL  = "gpt-4.1-mini"
TRANSLATION_MODEL = "gpt-4.1-mini"

PRICING = {"input": 0.40, "output": 1.60}   # USD per million tokens

MAX_RETRIES = 2   # gate failures trigger a retry with higher temperature

# ---------------------------------------------------------------------------
# Corpus matrix  (18 entries: 2 scenes × 3 pairs × 3 traits)
# ---------------------------------------------------------------------------

CORPUS: list[dict] = [
    # ── Scene 1: castle_throne_room ─────────────────────────────────────
    {
        "treeId":    "throneroom_knight_princess_brave_001",
        "scenarioId": "throneroom_brave_story",
        "scene":     "castle_throne_room",
        "pair":      "knight_princess",
        "traitId":   "BRAVE",
        "setting":   "Castle throne room",
        "prompt":    (
            "The Knight is feeling BRAVE today. He wants to impress the Princess by telling her "
            "a (not too scary) story about his adventure in the forest. Generate a dialogue tree where "
            "Knight starts the conversation. Knight is the speaker."
        ),
    },
    {
        "treeId":    "throneroom_knight_princess_kind_001",
        "scenarioId": "throneroom_kind_sharing",
        "scene":     "castle_throne_room",
        "pair":      "knight_princess",
        "traitId":   "KIND",
        "setting":   "Castle throne room",
        "prompt":    (
            "The Knight is KIND. He notices the Princess looks hungry and offers to share "
            "his snack with her. Generate a dialogue tree where Knight starts. Knight is speaker."
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
            "but she is too shy to ask the Knight directly. Generate a dialogue tree where "
            "Princess finally tries to ask. Princess is speaker."
        ),
    },
    {
        "treeId":    "throneroom_princess_dragon_curious_001",
        "scenarioId": "throneroom_curious_fire",
        "scene":     "castle_throne_room",
        "pair":      "princess_dragon",
        "traitId":   "CURIOUS",
        "setting":   "Castle throne room",
        "prompt":    (
            "The Princess is CURIOUS. She sees the Dragon sitting by the fireplace and wonders "
            "how the Dragon makes fire. She decides to ask. Princess is speaker."
        ),
    },
    {
        "treeId":    "throneroom_princess_dragon_silly_001",
        "scenarioId": "throneroom_silly_laugh",
        "scene":     "castle_throne_room",
        "pair":      "princess_dragon",
        "traitId":   "SILLY",
        "setting":   "Castle throne room",
        "prompt":    (
            "The Dragon is being SILLY, making funny faces at the wrong moment while the Princess "
            "is trying to read an important letter. Generate a dialogue tree. Dragon is speaker."
        ),
    },
    {
        "treeId":    "throneroom_princess_dragon_grumpy_001",
        "scenarioId": "throneroom_grumpy_woken",
        "scene":     "castle_throne_room",
        "pair":      "princess_dragon",
        "traitId":   "GRUMPY",
        "setting":   "Castle throne room",
        "prompt":    (
            "The Dragon is GRUMPY because Princess accidentally woke her up from her nap. "
            "Dragon grumbles at Princess. Generate a dialogue tree. Dragon is speaker."
        ),
    },
    {
        "treeId":    "throneroom_knight_dragon_brave_001",
        "scenarioId": "throneroom_brave_challenge",
        "scene":     "castle_throne_room",
        "pair":      "knight_dragon",
        "traitId":   "BRAVE",
        "setting":   "Castle throne room",
        "prompt":    (
            "The Knight is BRAVE. He challenges Dragon to a friendly game of 'who can roar loudest'. "
            "Generate a dialogue tree where Knight starts the challenge. Knight is speaker."
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
            "The Knight is KIND. He has brought Dragon a big bowl of apples as a gift. "
            "Generate a dialogue tree of Knight presenting the gift. Knight is speaker."
        ),
    },
    {
        "treeId":    "throneroom_knight_dragon_curious_001",
        "scenarioId": "throneroom_curious_helmet",
        "scene":     "castle_throne_room",
        "pair":      "knight_dragon",
        "traitId":   "CURIOUS",
        "setting":   "Castle throne room",
        "prompt":    (
            "The Dragon is CURIOUS. Dragon wonders why Knight always wears his heavy helmet "
            "even inside the warm throne room. Dragon asks. Dragon is speaker."
        ),
    },

    # ── Scene 2: castle_courtyard ────────────────────────────────────────
    {
        "treeId":    "courtyard_knight_princess_kind_001",
        "scenarioId": "courtyard_kind_flowers",
        "scene":     "castle_courtyard",
        "pair":      "knight_princess",
        "traitId":   "KIND",
        "setting":   "Castle courtyard (outdoor, sunny, flowers and a fountain)",
        "prompt":    (
            "The Knight is KIND. He is helping Princess water the courtyard flowers. "
            "He starts chatting with her about the flowers. Knight is speaker."
        ),
    },
    {
        "treeId":    "courtyard_knight_princess_curious_001",
        "scenarioId": "courtyard_curious_morning",
        "scene":     "castle_courtyard",
        "pair":      "knight_princess",
        "traitId":   "CURIOUS",
        "setting":   "Castle courtyard",
        "prompt":    (
            "The Princess is CURIOUS. She wonders where Knight goes every morning with his horse. "
            "She decides to ask him in the courtyard. Princess is speaker."
        ),
    },
    {
        "treeId":    "courtyard_knight_princess_silly_001",
        "scenarioId": "courtyard_silly_swords",
        "scene":     "castle_courtyard",
        "pair":      "knight_princess",
        "traitId":   "SILLY",
        "setting":   "Castle courtyard",
        "prompt":    (
            "The Knight is being SILLY. He is practicing funny sword tricks with a stick and "
            "keeps tripping over his own feet. Princess watches. Knight is speaker."
        ),
    },
    {
        "treeId":    "courtyard_princess_dragon_brave_001",
        "scenarioId": "courtyard_brave_storm",
        "scene":     "castle_courtyard",
        "pair":      "princess_dragon",
        "traitId":   "BRAVE",
        "setting":   "Castle courtyard",
        "prompt":    (
            "There is a thunderstorm. Dragon is scared of the thunder. The Princess is BRAVE "
            "and tries to comfort Dragon. Princess is speaker."
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
            "Princess shares her favourite flowers with Dragon. Princess is speaker."
        ),
    },
    {
        "treeId":    "courtyard_princess_dragon_shy_001",
        "scenarioId": "courtyard_shy_join",
        "scene":     "castle_courtyard",
        "pair":      "princess_dragon",
        "traitId":   "SHY",
        "setting":   "Castle courtyard",
        "prompt":    (
            "Dragon is SHY. The other characters are playing in the courtyard. Dragon stands at "
            "the edge, too shy to join. Princess tries to invite Dragon over. Princess is speaker."
        ),
    },
    {
        "treeId":    "courtyard_knight_dragon_grumpy_001",
        "scenarioId": "courtyard_grumpy_apples",
        "scene":     "castle_courtyard",
        "pair":      "knight_dragon",
        "traitId":   "GRUMPY",
        "setting":   "Castle courtyard (apple tree)",
        "prompt":    (
            "Dragon is GRUMPY because Dragon ate ALL the courtyard apples from the apple tree. "
            "Knight discovers the empty tree and talks to Dragon about it. Knight is speaker."
        ),
    },
    {
        "treeId":    "courtyard_knight_dragon_brave_001",
        "scenarioId": "courtyard_brave_tower",
        "scene":     "castle_courtyard",
        "pair":      "knight_dragon",
        "traitId":   "BRAVE",
        "setting":   "Castle courtyard (tall tower visible)",
        "prompt":    (
            "The Knight is BRAVE. He dares Dragon to fly over the tall tower. Dragon is nervous. "
            "Knight encourages Dragon. Knight is speaker."
        ),
    },
    {
        "treeId":    "courtyard_knight_dragon_shy_001",
        "scenarioId": "courtyard_shy_friends",
        "scene":     "castle_courtyard",
        "pair":      "knight_dragon",
        "traitId":   "SHY",
        "setting":   "Castle courtyard",
        "prompt":    (
            "The Knight is SHY. He wants Dragon to be his best friend but is too shy to say so. "
            "He works up the courage to ask. Knight is speaker."
        ),
    },
]


# ---------------------------------------------------------------------------
# System prompt (Structured-Output compatible)
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
3. Minimum tree depth: 2 levels. Maximum depth: 3 levels.
4. Every leaf node (branches = []) MUST have "outcome": "MOOD_POSITIVE"|"MOOD_NEGATIVE"|"NEUTRAL".
5. Non-leaf nodes MUST NOT have an "outcome" field.
6. Every "targetNodeId" MUST reference an existing "nodeId" in the nodes array.
7. No unreachable nodes (every node except node_0 must be reachable from node_0).
8. "tone" must be FRIENDLY, NEUTRAL, or GRUMPY (uppercase, no other values).
9. Outcomes must include at least one MOOD_POSITIVE and at least one MOOD_NEGATIVE leaf.
10. All text must be appropriate for a 7-year-old: short sentences, simple words, no scary content.
11. Language: EN only in characterLine.en and playerLabel.en fields.

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
# Gate validators (inline — same logic as o2_dialogue_quality.py)
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


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    api_key = os.environ.get("OPENAI_API_KEY","").strip().strip('"').strip("'")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not set.", file=sys.stderr); sys.exit(1)
    client = openai.OpenAI(api_key=api_key)

    total_cost = 0.0
    all_results = []
    gate_failures = 0
    catalogue = []

    print(f"O-8 Bulk Corpus Sprint — {len(CORPUS)} trees")
    print(f"Model: {GENERATION_MODEL} | Output: assets/dialogue/")
    print("="*60)

    for i, entry in enumerate(CORPUS, 1):
        tid = entry["treeId"]
        print(f"\n[{i:02d}/{len(CORPUS)}] {tid}")

        # --- Pass 1: EN generation (with retry on gate failure) ---
        en_tree = None
        gen_meta = {}
        for attempt in range(1, MAX_RETRIES + 1):
            temp = 0.7 + (attempt - 1) * 0.2   # raise temp on retry
            print(f"  EN gen (attempt {attempt}, T={temp:.1f})...", end="", flush=True)
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
                                    for k,v in gates.items() if k != "overall")
                print(f"  Gates: {gate_sym}")
                break
            else:
                # Print failures
                fails = [f"{k}: {v['detail']}" for k,v in gates.items()
                         if k != "overall" and not v["pass"]]
                print(f"  Gates: ❌ FAIL: {' | '.join(fails)}")
                if attempt < MAX_RETRIES:
                    print(f"  → retry {attempt+1}")
                    en_tree = None   # force retry

        if en_tree is None or not gates.get("overall"):
            print(f"  ❌ SKIPPED after {MAX_RETRIES} attempts")
            gate_failures += 1
            all_results.append({"treeId": tid, "status": "failed",
                                 "gates": gates if en_tree else {}, "gen_meta": gen_meta})
            continue

        # --- Pass 2: NL translation ---
        print(f"  NL trans...", end="", flush=True)
        nl_tree, nl_meta = translate_nl(client, en_tree)
        total_cost += nl_meta.get("cost", 0.0)

        if nl_tree is None:
            print(f" ❌ TRANSLATION ERROR: {nl_meta.get('err')}")
            # Still save EN-only tree rather than losing the work
            final_tree = en_tree
            print("  → saving EN-only tree (NL translation failed)")
        else:
            print(f" ✅ {nl_meta['ms']}ms ${nl_meta['cost']:.5f}")
            final_tree = nl_tree

        # --- Save ---
        out_filename = f"{entry['scene']}_{entry['pair']}_{entry['traitId'].lower()}.json"
        out_path = ASSETS_DIALOGUE / out_filename
        out_path.write_text(json.dumps(final_tree, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  Saved → assets/dialogue/{out_filename}")

        catalogue.append({
            "treeId":     tid,
            "file":       out_filename,
            "scene":      entry["scene"],
            "pair":       entry["pair"],
            "traitId":    entry["traitId"],
            "scenarioId": entry["scenarioId"],
            "hasNl":      nl_tree is not None,
        })

        all_results.append({
            "treeId":   tid,
            "status":   "ok",
            "gates":    {k: v["pass"] for k,v in gates.items() if k != "overall"},
            "gen_meta": gen_meta,
            "nl_meta":  nl_meta if nl_tree else None,
            "file":     out_filename,
        })

    # ---------------------------------------------------------------------------
    # Catalogue + report
    # ---------------------------------------------------------------------------
    cat_file = ASSETS_DIALOGUE / "catalogue.json"
    cat_file.write_text(json.dumps({
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "model": GENERATION_MODEL,
        "trees": catalogue,
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    (OUT_DIR / "gate_report.json").write_text(
        json.dumps({
            "total_trees":    len(CORPUS),
            "generated_ok":   len(CORPUS) - gate_failures,
            "gate_failures":  gate_failures,
            "total_cost_usd": round(total_cost, 4),
            "results":        all_results,
        }, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # ---------------------------------------------------------------------------
    # Prompt-log entry
    # ---------------------------------------------------------------------------
    total_in  = sum(r.get("gen_meta",{}).get("in",0) for r in all_results)
    total_out = sum(r.get("gen_meta",{}).get("out",0) for r in all_results)
    total_in  += sum(r.get("nl_meta",{}).get("in",0) for r in all_results if r.get("nl_meta"))
    total_out += sum(r.get("nl_meta",{}).get("out",0) for r in all_results if r.get("nl_meta"))

    log_entry = (
        f"\n## O-8 Bulk Corpus — {time.strftime('%Y-%m-%d')}\n\n"
        f"- **Model:** {GENERATION_MODEL}  \n"
        f"- **Trees generated:** {len(CORPUS) - gate_failures}/{len(CORPUS)}  \n"
        f"- **Gate failures:** {gate_failures}  \n"
        f"- **Total tokens:** {total_in}in / {total_out}out  \n"
        f"- **Total cost:** ${total_cost:.4f} USD  \n"
        f"- **Output path:** `assets/dialogue/`  \n"
    )
    if PROMPT_LOG.exists():
        existing = PROMPT_LOG.read_text(encoding="utf-8")
        PROMPT_LOG.write_text(existing + log_entry, encoding="utf-8")
    else:
        PROMPT_LOG.write_text(f"# Prompt Log\n{log_entry}", encoding="utf-8")

    # ---------------------------------------------------------------------------
    # Summary
    # ---------------------------------------------------------------------------
    print(f"\n{'='*60}")
    print(f"O-8 COMPLETE")
    print(f"  Trees:      {len(CORPUS) - gate_failures}/{len(CORPUS)} generated")
    print(f"  Failures:   {gate_failures}")
    print(f"  Total cost: ${total_cost:.4f}")
    print(f"  Catalogue:  assets/dialogue/catalogue.json ({len(catalogue)} entries)")
    print(f"\nO-8 GATE: {'PASS ✅' if gate_failures == 0 else f'PARTIAL ⚠️ ({gate_failures} trees failed)'}")


if __name__ == "__main__":
    main()
