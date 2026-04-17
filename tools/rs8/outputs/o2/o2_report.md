# RS-7 O-2 — Dialogue Quality Spike Report

**Date:** 2026-04-17

## Model Results

| Model | Trees passed | Trees total | Total cost |
|---|---|---|---|
| `gpt-4.1` | 2 | 2 | $0.01808 |
| `gpt-4.1-mini` | 2 | 2 | $0.00384 |

## Gate Pass Rates

| Gate | gpt-4.1 | gpt-4.1-mini |
|---|---|---|
| 1_schema_valid | ✅ 2/2 | ✅ 2/2 |
| 2_graph_integrity | ✅ 2/2 | ✅ 2/2 |
| 3_branch_count | ✅ 2/2 | ✅ 2/2 |
| 4_depth | ✅ 2/2 | ✅ 2/2 |
| 5_leaf_outcomes | ✅ 2/2 | ✅ 2/2 |
| 6_tone_enum | ✅ 2/2 | ✅ 2/2 |
| 7_vocabulary | ✅ 2/2 | ✅ 2/2 |
| 8_content | ✅ 2/2 | ✅ 2/2 |

## Recommended model for O-8: `gpt-4.1-mini`
