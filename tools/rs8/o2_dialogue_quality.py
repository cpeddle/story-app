"""
RS-7 O-2 — Dialogue Quality Spike
===================================
Generates 2 EN dialogue trees per model (gpt-4.1 and gpt-4.1-mini) against the
RS-2 flat-array schema. Evaluates all 8 hard gates and produces a side-by-side
model comparison report.

Usage:
    cd tools
    uv run --with python-dotenv python rs7/o2_dialogue_quality.py

Outputs:
    tools/rs7/outputs/o2/gpt-4.1/tree_{n}.json
    tools/rs7/outputs/o2/gpt-4.1-mini/tree_{n}.json
    tools/rs7/outputs/o2/o2_report.json      — gate results + cost comparison
    tools/rs7/outputs/o2/o2_report.md        — human-readable summary

Preconditions:
    tools/.env: OPENAI_API_KEY=sk-...
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

ENV_FILE = Path(__file__).parent.parent / ".env"
if ENV_FILE.exists():
    from dotenv import load_dotenv
    load_dotenv(ENV_FILE)

import openai

OUT_DIR = Path(__file__).parent / "outputs" / "o2"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# RS-2 Schema Generation Prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a bilingual dialogue writer for a children's fantasy play app.
Target audience: 7-year-old children. Language register: warm, simple, encouraging.

OUTPUT FORMAT: Respond with a single valid JSON object. No markdown fences, no commentary.

The JSON must match this exact schema:
{
  "treeId": string,           // e.g. "throneroom_brave_001"
  "scenarioId": string,       // e.g. "castle_throne_sharing"
  "traitId": string,          // one of: BRAVE, SHY, KIND, SILLY, GRUMPY, CURIOUS
  "rootNodeId": "node_0",
  "nodes": [                  // FLAT array — all nodes at same level
    {
      "nodeId": string,       // "node_0", "node_1", etc.
      "speaker": "character", // always "character" (character speaks the line)
      "characterLine": {
        "en": string          // simple English, max Grade 2.5 reading level
        // NL omitted for now
      },
      "tone": string,         // MUST be one of: FRIENDLY, NEUTRAL, GRUMPY
      "branches": [           // empty array [] on leaf nodes
        {
          "branchId": string, // "br_0_1", "br_0_2", etc.
          "playerLabel": {
            "en": string      // player choice text — short, simple
          },
          "targetNodeId": string  // must reference a valid nodeId in nodes array
        }
      ],
      "outcome": string       // ONLY on leaf nodes (empty branches); one of: MOOD_POSITIVE, MOOD_NEGATIVE, NEUTRAL
                              // OMIT outcome on non-leaf nodes
    }
  ]
}

STRUCTURAL RULES — YOU MUST FOLLOW ALL OF THESE:
1. Root node (node_0) MUST have exactly 3 branches (player choices).
2. Every non-leaf node MUST have 2, 3, or 4 branches.
3. Minimum tree depth: 2 levels. Maximum depth: 3 levels.
4. Every leaf node (branches = []) MUST have an "outcome" field.
5. Every non-leaf node MUST NOT have an "outcome" field.
6. Every "targetNodeId" in every branch MUST match an existing "nodeId" in the nodes array.
7. No unreachable nodes. Every node except node_0 must be reachable from node_0.
8. "tone" must be exactly FRIENDLY, NEUTRAL, or GRUMPY (uppercase, no other values).
9. Outcomes must be distributed: at least one MOOD_POSITIVE, at least one MOOD_NEGATIVE leaf.
10. All text must be appropriate for a 7-year-old: short sentences, simple words, no scary content.

CONTENT: Fantasy castle setting. Two characters: Princess and Knight."""

TREE_SCENARIOS = [
    {
        "label": "tree_1_sharing_the_crown",
        "user_prompt": (
            "Generate a dialogue tree where the Princess finds the Knight wearing her favourite crown "
            "without asking. She decides to talk to him about it. "
            "Use traitId: CURIOUS. TreeId: throneroom_curious_001. ScenarioId: castle_crown_sharing."
        ),
    },
    {
        "label": "tree_2_helping_in_kitchen",
        "user_prompt": (
            "Generate a dialogue tree where the Knight wants help carrying heavy bags of flour to "
            "the castle kitchen, and asks the Princess. "
            "Use traitId: KIND. TreeId: courtyard_kind_001. ScenarioId: castle_kitchen_help."
        ),
    },
]

MODELS = ["gpt-4.1", "gpt-4.1-mini"]

# Approximate pricing (USD per million tokens) — April 2026
PRICING = {
    "gpt-4.1":      {"input": 2.00, "output": 8.00},
    "gpt-4.1-mini": {"input": 0.40, "output": 1.60},
}


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------

def generate_tree(client: openai.OpenAI, model: str, scenario: dict) -> tuple[dict | None, dict]:
    """Generate a dialogue tree. Returns (parsed_tree, meta) where meta has cost/latency."""
    t0 = time.perf_counter()
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": scenario["user_prompt"]},
            ],
            response_format={"type": "json_object"},
            temperature=0.7,
            max_tokens=2000,
        )
        latency_ms = round((time.perf_counter() - t0) * 1000)
        raw = response.choices[0].message.content or ""
        usage = response.usage
        in_tok  = usage.prompt_tokens     if usage else 0
        out_tok = usage.completion_tokens if usage else 0
        rates   = PRICING.get(model, {"input": 0.0, "output": 0.0})
        cost    = (in_tok / 1_000_000) * rates["input"] + (out_tok / 1_000_000) * rates["output"]

        try:
            tree = json.loads(raw)
        except json.JSONDecodeError as e:
            return None, {
                "model": model, "scenario": scenario["label"],
                "latency_ms": latency_ms, "in_tokens": in_tok, "out_tokens": out_tok,
                "cost_usd": round(cost, 6), "parse_error": str(e), "raw": raw[:500],
            }

        return tree, {
            "model": model, "scenario": scenario["label"],
            "latency_ms": latency_ms, "in_tokens": in_tok, "out_tokens": out_tok,
            "cost_usd": round(cost, 6), "parse_error": None,
        }
    except Exception as exc:
        return None, {
            "model": model, "scenario": scenario["label"],
            "latency_ms": round((time.perf_counter() - t0) * 1000),
            "in_tokens": 0, "out_tokens": 0, "cost_usd": 0.0,
            "parse_error": str(exc),
        }


# ---------------------------------------------------------------------------
# Hard Gates (8 total)
# ---------------------------------------------------------------------------

VALID_TONES     = {"FRIENDLY", "NEUTRAL", "GRUMPY"}
VALID_OUTCOMES  = {"MOOD_POSITIVE", "MOOD_NEGATIVE", "NEUTRAL"}
REQUIRED_TREE_FIELDS  = {"treeId", "scenarioId", "traitId", "rootNodeId", "nodes"}
REQUIRED_NODE_FIELDS  = {"nodeId", "speaker", "characterLine", "tone", "branches"}

def gate1_schema_valid(tree: dict) -> tuple[bool, str]:
    """Gate 1: required fields present at tree and node level."""
    missing_tree = REQUIRED_TREE_FIELDS - set(tree.keys())
    if missing_tree:
        return False, f"Missing tree fields: {missing_tree}"
    if not isinstance(tree.get("nodes"), list) or len(tree["nodes"]) == 0:
        return False, "nodes must be a non-empty list"
    issues = []
    for n in tree["nodes"]:
        missing = REQUIRED_NODE_FIELDS - set(n.keys())
        if missing:
            issues.append(f"Node {n.get('nodeId','?')}: missing {missing}")
        if not isinstance(n.get("characterLine"), dict) or "en" not in n.get("characterLine", {}):
            issues.append(f"Node {n.get('nodeId','?')}: characterLine.en missing")
    if issues:
        return False, "; ".join(issues[:3])
    return True, "ok"


def gate2_graph_integrity(tree: dict) -> tuple[bool, str]:
    """Gate 2: all targetNodeIds resolve; every node is reachable from root."""
    node_ids = {n["nodeId"] for n in tree["nodes"]}
    root_id  = tree.get("rootNodeId", "node_0")

    # Check all targetNodeIds resolve
    bad_refs = []
    for n in tree["nodes"]:
        for br in n.get("branches", []):
            tid = br.get("targetNodeId")
            if tid not in node_ids:
                bad_refs.append(f"{n['nodeId']}->{tid}")
    if bad_refs:
        return False, f"Dangling targetNodeIds: {bad_refs[:3]}"

    # BFS reachability from root
    reachable = set()
    queue = deque([root_id])
    nodes_by_id = {n["nodeId"]: n for n in tree["nodes"]}
    while queue:
        nid = queue.popleft()
        if nid in reachable:
            continue
        reachable.add(nid)
        node = nodes_by_id.get(nid)
        if node:
            for br in node.get("branches", []):
                queue.append(br["targetNodeId"])

    unreachable = node_ids - reachable
    if unreachable:
        return False, f"Unreachable nodes: {unreachable}"
    return True, f"ok ({len(node_ids)} nodes, all reachable)"


def gate3_branch_count(tree: dict) -> tuple[bool, str]:
    """Gate 3: root ≥3 branches; all non-leaf 2–4 branches."""
    root_id    = tree.get("rootNodeId", "node_0")
    issues     = []
    nodes_by_id = {n["nodeId"]: n for n in tree["nodes"]}
    for n in tree["nodes"]:
        b = len(n.get("branches", []))
        is_leaf = (b == 0)
        if is_leaf:
            continue
        nid = n["nodeId"]
        if nid == root_id:
            if b < 3:
                issues.append(f"Root has {b} branches (need ≥3)")
        else:
            if not (2 <= b <= 4):
                issues.append(f"Node {nid} has {b} branches (need 2–4)")
    if issues:
        return False, "; ".join(issues)
    return True, "ok"


def gate4_depth(tree: dict) -> tuple[bool, str]:
    """Gate 4: min depth ≥2, max depth ≤3."""
    root_id     = tree.get("rootNodeId", "node_0")
    nodes_by_id = {n["nodeId"]: n for n in tree["nodes"]}

    depths: dict[str, int] = {}
    queue = deque([(root_id, 0)])
    while queue:
        nid, d = queue.popleft()
        if nid in depths:
            continue
        depths[nid] = d
        node = nodes_by_id.get(nid)
        if node:
            for br in node.get("branches", []):
                queue.append((br["targetNodeId"], d + 1))

    max_depth = max(depths.values()) if depths else 0
    leaves    = [nid for nid, n in nodes_by_id.items()
                 if len(n.get("branches", [])) == 0]
    leaf_depths = [depths.get(l, 0) for l in leaves]
    min_leaf_depth = min(leaf_depths) if leaf_depths else 0

    if min_leaf_depth < 1:
        return False, f"Some leaves at depth {min_leaf_depth} (min 1 level deep means depth ≥1 from root)"
    if max_depth < 2:
        return False, f"Max depth is {max_depth} (need ≥2)"
    if max_depth > 3:
        return False, f"Max depth is {max_depth} (need ≤3)"
    return True, f"ok (max depth {max_depth}, min leaf depth {min_leaf_depth})"


def gate5_leaf_outcomes(tree: dict) -> tuple[bool, str]:
    """Gate 5: every leaf has a valid outcome; non-leaves have none."""
    issues = []
    for n in tree["nodes"]:
        is_leaf = len(n.get("branches", [])) == 0
        outcome = n.get("outcome")
        if is_leaf:
            if outcome not in VALID_OUTCOMES:
                issues.append(f"Leaf {n['nodeId']} has invalid outcome: {outcome!r}")
        else:
            if outcome is not None:
                issues.append(f"Non-leaf {n['nodeId']} has outcome {outcome!r}")
    if issues:
        return False, "; ".join(issues[:3])
    # Also check distribution: at least one positive and one negative
    leaf_outcomes = [n.get("outcome") for n in tree["nodes"] if len(n.get("branches", [])) == 0]
    if "MOOD_POSITIVE" not in leaf_outcomes:
        return False, "No MOOD_POSITIVE leaf outcome (no path to positive mood)"
    if "MOOD_NEGATIVE" not in leaf_outcomes:
        return False, "No MOOD_NEGATIVE leaf outcome (no path to negative mood)"
    return True, f"ok (outcomes: {sorted(set(leaf_outcomes))})"


def gate6_tone_enum(tree: dict) -> tuple[bool, str]:
    """Gate 6: every node tone is FRIENDLY, NEUTRAL, or GRUMPY."""
    bad = [f"{n['nodeId']}:{n.get('tone')!r}"
           for n in tree["nodes"] if n.get("tone") not in VALID_TONES]
    if bad:
        return False, f"Invalid tones: {bad[:3]}"
    return True, "ok"


def _count_syllables(word: str) -> int:
    """Very simple English syllable counter for FK approximation."""
    word = word.lower().strip(".,!?\"'")
    if not word:
        return 0
    # Count vowel groups
    vowels  = "aeiouy"
    count   = 0
    in_vowel = False
    for ch in word:
        if ch in vowels:
            if not in_vowel:
                count += 1
            in_vowel = True
        else:
            in_vowel = False
    # Silent e at end
    if word.endswith("e") and count > 1:
        count -= 1
    return max(1, count)


def _flesch_kincaid_grade(text: str) -> float:
    """Approximate Flesch-Kincaid Grade Level for a block of text."""
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    words     = re.findall(r"\b[a-zA-Z']+\b", text)
    if not sentences or not words:
        return 0.0
    syllable_count = sum(_count_syllables(w) for w in words)
    asl = len(words) / len(sentences)       # avg sentence length
    asw = syllable_count / len(words)       # avg syllables per word
    grade = 0.39 * asl + 11.8 * asw - 15.59
    return round(grade, 2)


def gate7_vocabulary(tree: dict) -> tuple[bool, str]:
    """Gate 7: FK grade ≤2.5 for all EN text combined."""
    texts = []
    for n in tree["nodes"]:
        cl = n.get("characterLine", {})
        if cl.get("en"):
            texts.append(cl["en"])
        for br in n.get("branches", []):
            pl = br.get("playerLabel", {})
            if pl.get("en"):
                texts.append(pl["en"])
    combined = " ".join(texts)
    grade = _flesch_kincaid_grade(combined)
    if grade > 2.5:
        return False, f"FK grade {grade} exceeds 2.5"
    return True, f"ok (FK grade ≈{grade})"


def gate8_content(client: openai.OpenAI, tree: dict) -> tuple[bool, str]:
    """Gate 8: OpenAI Moderation API — all EN text must be clean."""
    texts = []
    for n in tree["nodes"]:
        cl = n.get("characterLine", {})
        if cl.get("en"):
            texts.append(cl["en"])
        for br in n.get("branches", []):
            pl = br.get("playerLabel", {})
            if pl.get("en"):
                texts.append(pl["en"])

    flagged = []
    for text in texts:
        try:
            r      = client.moderations.create(input=text, model="omni-moderation-latest")
            result = r.results[0]
            if result.flagged:
                cats = [k for k, v in vars(result.categories).items() if v]
                flagged.append(f"'{text[:40]}': {cats}")
        except Exception as exc:
            # Don't fail the whole gate on a transient API error
            flagged.append(f"moderation_error: {exc}")

    if flagged:
        return False, f"Flagged: {flagged[:2]}"
    return True, f"ok ({len(texts)} strings checked)"


def run_all_gates(client: openai.OpenAI, tree: dict) -> dict:
    """Run all 8 hard gates. Returns dict of gate_name -> {pass, detail}."""
    gates = {}

    for idx, (name, fn) in enumerate([
        ("1_schema_valid",    lambda t: gate1_schema_valid(t)),
        ("2_graph_integrity", lambda t: gate2_graph_integrity(t)),
        ("3_branch_count",    lambda t: gate3_branch_count(t)),
        ("4_depth",           lambda t: gate4_depth(t)),
        ("5_leaf_outcomes",   lambda t: gate5_leaf_outcomes(t)),
        ("6_tone_enum",       lambda t: gate6_tone_enum(t)),
        ("7_vocabulary",      lambda t: gate7_vocabulary(t)),
        ("8_content",         lambda t: gate8_content(client, t)),
    ], 1):
        try:
            passed, detail = fn(tree)
        except Exception as exc:
            passed, detail = False, f"exception: {exc}"
        gates[name] = {"pass": passed, "detail": detail}

    gates["overall_pass"] = all(v["pass"] for k, v in gates.items() if k != "overall_pass")
    return gates


# ---------------------------------------------------------------------------
# Soft quality scoring (quick heuristic, not a full rubric)
# ---------------------------------------------------------------------------

def soft_score(tree: dict) -> dict:
    """Quick heuristic soft quality indicators (not a full 6-dimension rubric)."""
    nodes      = tree.get("nodes", [])
    leaves     = [n for n in nodes if len(n.get("branches", [])) == 0]
    outcomes   = [n.get("outcome") for n in leaves]
    n_pos      = outcomes.count("MOOD_POSITIVE")
    n_neg      = outcomes.count("MOOD_NEGATIVE")
    n_neu      = outcomes.count("NEUTRAL")
    balance    = round(1.0 - abs(n_pos - n_neg) / max(len(leaves), 1), 2)

    total_words = sum(
        len(re.findall(r"\b\w+\b", n.get("characterLine", {}).get("en", "")))
        for n in nodes
    )
    avg_words_per_node = round(total_words / max(len(nodes), 1), 1)

    return {
        "node_count":        len(nodes),
        "leaf_count":        len(leaves),
        "outcome_balance":   balance,      # 1.0 = perfectly balanced pos/neg
        "outcomes":          {"MOOD_POSITIVE": n_pos, "MOOD_NEGATIVE": n_neg, "NEUTRAL": n_neu},
        "avg_words_per_node": avg_words_per_node,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip().strip('"').strip("'")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not set.", file=sys.stderr)
        sys.exit(1)

    client = openai.OpenAI(api_key=api_key)

    all_results: list[dict] = []
    totals: dict[str, float] = {m: 0.0 for m in MODELS}

    for model in MODELS:
        model_dir = OUT_DIR / model
        model_dir.mkdir(parents=True, exist_ok=True)
        print(f"\n{'='*60}")
        print(f"MODEL: {model}")
        print(f"{'='*60}")

        for i, scenario in enumerate(TREE_SCENARIOS, 1):
            print(f"\n  [{model}] Scenario {i}: {scenario['label']}")
            print(f"  Generating...", end="", flush=True)

            tree, meta = generate_tree(client, model, scenario)
            totals[model] += meta.get("cost_usd", 0.0)

            if tree is None:
                print(f" ❌ PARSE/API ERROR: {meta.get('parse_error')}")
                gate_results = {f"{n}_gate": {"pass": False, "detail": "generation_failed"}
                                for n in ["1","2","3","4","5","6","7","8"]}
                gate_results["overall_pass"] = False
            else:
                print(f" ✅ ({meta['latency_ms']} ms, {meta['in_tokens']}in/{meta['out_tokens']}out, ${meta['cost_usd']:.5f})")

                # Save raw tree
                out_file = model_dir / f"tree_{i}_{scenario['label']}.json"
                out_file.write_text(json.dumps(tree, indent=2, ensure_ascii=False), encoding="utf-8")
                print(f"     Saved: {out_file.name}")

                # Run gates
                print(f"     Gates:", end=" ")
                gate_results = run_all_gates(client, tree)
                for gname, gval in gate_results.items():
                    if gname == "overall_pass":
                        continue
                    sym = "✅" if gval["pass"] else "❌"
                    print(sym, end=" ")
                print()

                for gname, gval in gate_results.items():
                    if gname == "overall_pass":
                        continue
                    if not gval["pass"]:
                        print(f"       ❌ {gname}: {gval['detail']}")

                # Soft score
                sq = soft_score(tree)
                print(f"     Soft: {sq['node_count']} nodes, "
                      f"{sq['leaf_count']} leaves, "
                      f"balance={sq['outcome_balance']}, "
                      f"~{sq['avg_words_per_node']} words/node")

            all_results.append({
                "model":    model,
                "scenario": scenario["label"],
                "meta":     meta,
                "gates":    gate_results,
                "soft":     soft_score(tree) if tree else None,
                "tree":     tree,
            })

    # ---------------------------------------------------------------------------
    # Summary report
    # ---------------------------------------------------------------------------
    print(f"\n{'='*60}")
    print("O-2 SUMMARY")
    print(f"{'='*60}")

    model_pass_counts: dict[str, int] = {m: 0 for m in MODELS}
    model_total_counts: dict[str, int] = {m: 0 for m in MODELS}

    for r in all_results:
        m = r["model"]
        model_total_counts[m] += 1
        if r["gates"].get("overall_pass"):
            model_pass_counts[m] += 1

    for m in MODELS:
        pct = 100 * model_pass_counts[m] // max(model_total_counts[m], 1)
        print(f"  {m:<20} {model_pass_counts[m]}/{model_total_counts[m]} trees pass all gates  "
              f"| total cost ${totals[m]:.5f}")

    # Per-gate pass rates
    print(f"\n  Gate pass rates:")
    gate_names = [k for k in all_results[0]["gates"].keys() if k != "overall_pass"]
    header = f"  {'Gate':<25}" + "".join(f"  {m[:12]:<14}" for m in MODELS)
    print(header)
    for gname in gate_names:
        row = f"  {gname:<25}"
        for m in MODELS:
            model_results = [r for r in all_results if r["model"] == m]
            passes = sum(1 for r in model_results if r["gates"].get(gname, {}).get("pass"))
            total  = len(model_results)
            sym    = "✅" if passes == total else ("⚠️" if passes > 0 else "❌")
            row   += f"  {sym} {passes}/{total}          "
        print(row)

    # Recommendation
    print(f"\n  RECOMMENDATION:")
    if all(model_pass_counts[m] == model_total_counts[m] for m in MODELS):
        print("  ✅ Both models pass all gates.")
        print("  → Use gpt-4.1-mini for O-8 bulk sprint (~10× cheaper, same quality).")
        rec = "gpt-4.1-mini"
    elif model_pass_counts.get("gpt-4.1-mini", 0) == model_total_counts.get("gpt-4.1-mini", 1):
        print("  ✅ gpt-4.1-mini passes all gates.")
        print("  → Use gpt-4.1-mini for O-8 bulk sprint.")
        rec = "gpt-4.1-mini"
    elif model_pass_counts.get("gpt-4.1", 0) == model_total_counts.get("gpt-4.1", 1):
        print("  ⚠️  Only gpt-4.1 passes. Use gpt-4.1 for O-8 (higher cost).")
        rec = "gpt-4.1"
    else:
        print("  ❌ Neither model passes all gates. Do NOT proceed to O-8.")
        print("     Review gate failures and refine system prompt.")
        rec = "none"

    # Write JSON report
    report = {
        "recommendation_model_for_o8": rec,
        "model_pass_counts":  model_pass_counts,
        "model_total_counts": model_total_counts,
        "model_total_cost":   {m: round(totals[m], 6) for m in MODELS},
        "results":            all_results,
    }
    report_json = OUT_DIR / "o2_report.json"
    # Omit raw tree text from report to keep it readable
    slim = {**report, "results": [{k: v for k, v in r.items() if k != "tree"}
                                   for r in all_results]}
    report_json.write_text(json.dumps(slim, indent=2, ensure_ascii=False), encoding="utf-8")

    # Write Markdown report
    md_lines = [
        "# RS-7 O-2 — Dialogue Quality Spike Report",
        "",
        f"**Date:** {time.strftime('%Y-%m-%d')}",
        "",
        "## Model Results",
        "",
        "| Model | Trees passed | Trees total | Total cost |",
        "|---|---|---|---|",
    ]
    for m in MODELS:
        md_lines.append(f"| `{m}` | {model_pass_counts[m]} | {model_total_counts[m]} | ${totals[m]:.5f} |")
    md_lines += ["", "## Gate Pass Rates", "", "| Gate | " + " | ".join(MODELS) + " |",
                 "|---|" + "---|" * len(MODELS)]
    for gname in gate_names:
        row = f"| {gname} |"
        for m in MODELS:
            model_results = [r for r in all_results if r["model"] == m]
            passes = sum(1 for r in model_results if r["gates"].get(gname, {}).get("pass"))
            row += f" {'✅' if passes == len(model_results) else '❌'} {passes}/{len(model_results)} |"
        md_lines.append(row)
    md_lines += ["", f"## Recommended model for O-8: `{rec}`", ""]
    (OUT_DIR / "o2_report.md").write_text("\n".join(md_lines), encoding="utf-8")

    print(f"\n✅ Reports written to {OUT_DIR}/")
    print(f"   o2_report.json, o2_report.md")
    overall = all(model_pass_counts[m] > 0 for m in MODELS) or model_pass_counts.get("gpt-4.1-mini", 0) > 0
    print(f"\nO-2 GATE: {'PASS ✅ — O-3, O-4, O-8 UNBLOCKED' if rec != 'none' else 'FAIL ❌ — O-8 BLOCKED'}")


if __name__ == "__main__":
    main()
