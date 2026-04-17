"""RS-5 scene-template evaluation scorer.

Scores LLM-generated scene templates against hand-authored ground-truth
templates using door detection, position accuracy, spawn plausibility,
zone coverage (IoU), schema compliance, and cross-run consistency.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from scipy.optimize import linear_sum_assignment


@dataclass
class TrialScore:
    """Scores for a single evaluation trial."""

    door_detection_rate: float = 0.0
    door_position_error: float = 0.0
    spawn_plausibility: float = 0.0
    zone_coverage: float = 0.0
    schema_compliance: float = 0.0
    consistency: float = 0.0
    weighted_score: float = 0.0
    details: dict = field(default_factory=dict)


class RS5Scorer:
    """RS-5-specific evaluation scorer."""

    WEIGHTS = {
        "door_detection": 0.25,
        "door_position": 0.25,
        "spawn_plausibility": 0.15,
        "zone_coverage": 0.15,
        "schema_compliance": 0.10,
        "consistency": 0.10,
    }
    POSITION_TOLERANCE = 0.10

    def __init__(self, ground_truth_dir: str, schema_path: str) -> None:
        self._ground_truths: dict[str, dict] = {}
        gt_dir = Path(ground_truth_dir)
        for gt_file in gt_dir.glob("*.json"):
            with open(gt_file) as f:
                data = json.load(f)
            self._ground_truths[data["sceneId"]] = data

        from llm_eval.validator import SchemaValidator

        self._validator = SchemaValidator(schema_path)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def score_trial(self, predicted_json: str, ground_truth_id: str) -> TrialScore:
        """Score a single trial output against ground truth."""
        score = TrialScore()

        validation = self._validator.validate(predicted_json)
        score.schema_compliance = 1.0 if validation.valid else 0.0

        if not validation.valid or validation.parsed is None:
            score.weighted_score = self._compute_weighted(score)
            score.details["validation_errors"] = validation.errors
            return score

        predicted = validation.parsed
        gt = self._ground_truths.get(ground_truth_id)
        if gt is None:
            score.details["error"] = f"No ground truth found for '{ground_truth_id}'"
            score.weighted_score = self._compute_weighted(score)
            return score

        score.door_detection_rate, score.door_position_error, door_details = (
            self._score_doors(predicted.get("doors", []), gt.get("doors", []))
        )
        score.details["doors"] = door_details

        score.spawn_plausibility, spawn_details = self._score_spawns(
            predicted.get("spawnPoints", []), gt
        )
        score.details["spawns"] = spawn_details

        score.zone_coverage, zone_details = self._score_zones(
            predicted.get("objectZones", []), gt.get("objectZones", [])
        )
        score.details["zones"] = zone_details

        score.weighted_score = self._compute_weighted(score)
        return score

    def score_consistency(self, trial_jsons: list[str]) -> float:
        """Pairwise Jaccard similarity of door/spawn IDs across runs."""
        if len(trial_jsons) < 2:
            return 1.0

        id_sets: list[set[str]] = []
        for tj in trial_jsons:
            try:
                parsed = json.loads(tj)
            except json.JSONDecodeError:
                id_sets.append(set())
                continue
            ids: set[str] = set()
            for door in parsed.get("doors", []):
                ids.add(door.get("id", ""))
            for sp in parsed.get("spawnPoints", []):
                ids.add(sp.get("id", ""))
            id_sets.append(ids)

        similarities: list[float] = []
        for i in range(len(id_sets)):
            for j in range(i + 1, len(id_sets)):
                union = id_sets[i] | id_sets[j]
                if not union:
                    similarities.append(1.0)
                else:
                    similarities.append(len(id_sets[i] & id_sets[j]) / len(union))

        return sum(similarities) / len(similarities) if similarities else 1.0

    # ------------------------------------------------------------------
    # Private scoring helpers
    # ------------------------------------------------------------------

    def _compute_weighted(self, score: TrialScore) -> float:
        return (
            self.WEIGHTS["door_detection"] * score.door_detection_rate
            + self.WEIGHTS["door_position"] * score.door_position_error
            + self.WEIGHTS["spawn_plausibility"] * score.spawn_plausibility
            + self.WEIGHTS["zone_coverage"] * score.zone_coverage
            + self.WEIGHTS["schema_compliance"] * score.schema_compliance
            + self.WEIGHTS["consistency"] * score.consistency
        )

    # -- Doors ---------------------------------------------------------

    def _score_doors(
        self, predicted: list[dict], ground_truth: list[dict]
    ) -> tuple[float, float, dict]:
        """Return (detection_rate, position_score, details)."""
        details: dict = {}
        n_gt = len(ground_truth)

        if n_gt == 0:
            return 1.0, 1.0, {"note": "no GT doors — vacuously correct"}

        if not predicted:
            return 0.0, 0.0, {"note": "no predicted doors"}

        gt_pos = np.array(
            [(d["position"]["x"], d["position"]["y"]) for d in ground_truth]
        )
        pred_pos = np.array(
            [(d["position"]["x"], d["position"]["y"]) for d in predicted]
        )

        # Cost matrix: Euclidean distances between every pred–GT pair
        cost = np.linalg.norm(pred_pos[:, None, :] - gt_pos[None, :, :], axis=2)

        row_idx, col_idx = linear_sum_assignment(cost)

        matched_distances = cost[row_idx, col_idx]
        tp = int(np.sum(matched_distances <= self.POSITION_TOLERANCE))

        detection_rate = tp / n_gt

        if tp == 0:
            position_score = 0.0
        else:
            tp_mask = matched_distances <= self.POSITION_TOLERANCE
            avg_dist = float(np.mean(matched_distances[tp_mask]))
            position_score = max(0.0, 1.0 - avg_dist / self.POSITION_TOLERANCE)

        details["tp"] = tp
        details["n_gt"] = n_gt
        details["n_pred"] = len(predicted)
        details["matched_distances"] = matched_distances.tolist()

        return detection_rate, position_score, details

    # -- Spawns --------------------------------------------------------

    def _score_spawns(
        self, predicted: list[dict], gt: dict
    ) -> tuple[float, dict]:
        """Return (plausibility_score, details)."""
        if not predicted:
            return 0.0, {"note": "no predicted spawns"}

        walkable_zones = [
            z
            for z in gt.get("objectZones", [])
            if any(
                kw in z.get("label", "").lower()
                for kw in ("floor", "path", "carpet")
            )
        ]
        gt_spawn_positions = [
            (sp["position"]["x"], sp["position"]["y"])
            for sp in gt.get("spawnPoints", [])
        ]

        plausible = 0
        per_spawn: list[dict] = []
        for sp in predicted:
            px, py = sp["position"]["x"], sp["position"]["y"]
            in_zone = any(self._point_in_rect(px, py, z["bounds"]) for z in walkable_zones)
            near_gt = any(
                _euclid(px, py, gx, gy) <= self.POSITION_TOLERANCE
                for gx, gy in gt_spawn_positions
            )
            ok = in_zone or near_gt
            if ok:
                plausible += 1
            per_spawn.append({"id": sp.get("id"), "plausible": ok})

        return plausible / len(predicted), {"per_spawn": per_spawn}

    # -- Zones (IoU) ---------------------------------------------------

    def _score_zones(
        self, predicted: list[dict], ground_truth: list[dict]
    ) -> tuple[float, dict]:
        """Return (avg_best_iou, details)."""
        if not ground_truth:
            return 1.0, {"note": "no GT zones — vacuously correct"}
        if not predicted:
            return 0.0, {"note": "no predicted zones"}

        best_ious: list[float] = []
        per_zone: list[dict] = []
        for gt_z in ground_truth:
            gt_b = gt_z["bounds"]
            best = 0.0
            for pr_z in predicted:
                iou = self._iou(gt_b, pr_z["bounds"])
                if iou > best:
                    best = iou
            best_ious.append(best)
            per_zone.append({"gt_id": gt_z.get("id"), "best_iou": best})

        return float(np.mean(best_ious)), {"per_zone": per_zone}

    # -- Geometry utilities --------------------------------------------

    @staticmethod
    def _point_in_rect(px: float, py: float, rect: dict) -> bool:
        return (
            rect["x"] <= px <= rect["x"] + rect["w"]
            and rect["y"] <= py <= rect["y"] + rect["h"]
        )

    @staticmethod
    def _iou(a: dict, b: dict) -> float:
        x1 = max(a["x"], b["x"])
        y1 = max(a["y"], b["y"])
        x2 = min(a["x"] + a["w"], b["x"] + b["w"])
        y2 = min(a["y"] + a["h"], b["y"] + b["h"])

        inter_w = max(0.0, x2 - x1)
        inter_h = max(0.0, y2 - y1)
        inter_area = inter_w * inter_h

        area_a = a["w"] * a["h"]
        area_b = b["w"] * b["h"]
        union_area = area_a + area_b - inter_area

        if union_area == 0:
            return 0.0
        return inter_area / union_area


def _euclid(x1: float, y1: float, x2: float, y2: float) -> float:
    return ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5
