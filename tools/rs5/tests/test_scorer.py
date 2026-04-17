"""Tests for the RS-5 scene-template scorer."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

# Paths relative to the rs5 tool root
_RS5_ROOT = Path(__file__).resolve().parent.parent
_GT_DIR = _RS5_ROOT / "ground-truth"
_SCHEMA = _RS5_ROOT / "schema" / "scene-template.schema.json"


@pytest.fixture()
def scorer():
    from scorer import RS5Scorer

    return RS5Scorer(str(_GT_DIR), str(_SCHEMA))


@pytest.fixture()
def corridor_gt() -> dict:
    with open(_GT_DIR / "castle-corridor.json") as f:
        return json.load(f)


@pytest.fixture()
def throne_gt() -> dict:
    with open(_GT_DIR / "castle-throne-room.json") as f:
        return json.load(f)


# ------------------------------------------------------------------
# 1. Perfect match — GT as prediction
# ------------------------------------------------------------------


class TestPerfectMatch:
    def test_corridor_perfect(self, scorer, corridor_gt):
        result = scorer.score_trial(json.dumps(corridor_gt), "castle-corridor")
        assert result.schema_compliance == 1.0
        assert result.door_detection_rate == 1.0
        assert result.door_position_error == 1.0
        assert result.spawn_plausibility == 1.0
        assert result.zone_coverage == pytest.approx(1.0)

    def test_throne_room_perfect(self, scorer, throne_gt):
        result = scorer.score_trial(json.dumps(throne_gt), "castle-throne-room")
        assert result.schema_compliance == 1.0
        assert result.door_detection_rate == 1.0
        assert result.door_position_error == 1.0


# ------------------------------------------------------------------
# 2. No doors found
# ------------------------------------------------------------------


class TestNoDoors:
    def test_empty_doors_array(self, scorer, corridor_gt):
        pred = copy.deepcopy(corridor_gt)
        pred["doors"] = []
        result = scorer.score_trial(json.dumps(pred), "castle-corridor")
        assert result.door_detection_rate == 0.0
        assert result.door_position_error == 0.0


# ------------------------------------------------------------------
# 3. Extra doors — all GT doors still matched
# ------------------------------------------------------------------


class TestExtraDoors:
    def test_extra_doors_still_detected(self, scorer, corridor_gt):
        pred = copy.deepcopy(corridor_gt)
        pred["doors"].append(
            {
                "id": "door-extra",
                "position": {"x": 0.50, "y": 0.50},
                "size": {"w": 0.05, "h": 0.15},
                "spawnPoint": {"x": 0.50, "y": 0.65},
            }
        )
        result = scorer.score_trial(json.dumps(pred), "castle-corridor")
        assert result.door_detection_rate == 1.0


# ------------------------------------------------------------------
# 4. Slightly shifted doors (within tolerance)
# ------------------------------------------------------------------


class TestShiftedDoors:
    def test_small_shift_within_tolerance(self, scorer, corridor_gt):
        pred = copy.deepcopy(corridor_gt)
        for door in pred["doors"]:
            door["position"]["x"] += 0.03
            door["position"]["y"] += 0.03
        result = scorer.score_trial(json.dumps(pred), "castle-corridor")
        assert result.door_detection_rate == 1.0
        assert result.door_position_error > 0.0
        # Position score should be less than perfect but still positive
        assert result.door_position_error < 1.0


# ------------------------------------------------------------------
# 5. Doors way off (> tolerance)
# ------------------------------------------------------------------


class TestDoorsWayOff:
    def test_large_shift_beyond_tolerance(self, scorer, corridor_gt):
        pred = copy.deepcopy(corridor_gt)
        for door in pred["doors"]:
            door["position"]["x"] = 0.99
            door["position"]["y"] = 0.01
        result = scorer.score_trial(json.dumps(pred), "castle-corridor")
        assert result.door_detection_rate == 0.0


# ------------------------------------------------------------------
# 6. Invalid JSON
# ------------------------------------------------------------------


class TestInvalidJSON:
    def test_malformed_string(self, scorer):
        result = scorer.score_trial("{not valid json!!!", "castle-corridor")
        assert result.schema_compliance == 0.0
        assert "validation_errors" in result.details

    def test_valid_json_but_bad_schema(self, scorer):
        result = scorer.score_trial('{"foo": "bar"}', "castle-corridor")
        assert result.schema_compliance == 0.0


# ------------------------------------------------------------------
# 7. Consistency
# ------------------------------------------------------------------


class TestConsistency:
    def test_identical_jsons(self, scorer, corridor_gt):
        jsons = [json.dumps(corridor_gt)] * 3
        assert scorer.score_consistency(jsons) == 1.0

    def test_different_door_ids(self, scorer, corridor_gt):
        a = copy.deepcopy(corridor_gt)
        b = copy.deepcopy(corridor_gt)
        c = copy.deepcopy(corridor_gt)
        b["doors"][0]["id"] = "door-totally-different"
        c["doors"][0]["id"] = "door-another-one"
        c["doors"][1]["id"] = "door-yet-another"
        result = scorer.score_consistency(
            [json.dumps(a), json.dumps(b), json.dumps(c)]
        )
        assert result < 1.0

    def test_single_trial(self, scorer, corridor_gt):
        assert scorer.score_consistency([json.dumps(corridor_gt)]) == 1.0


# ------------------------------------------------------------------
# 8. Zone IoU — 50% overlap
# ------------------------------------------------------------------


class TestZoneIoU:
    def test_half_overlap(self, scorer):
        """Predicted zone shifted right by half its width → IoU ≈ 1/3."""
        gt = {
            "sceneId": "test-iou",
            "displayNameKey": "t",
            "background": {"assetPath": "x.svg", "width": 1920, "height": 1080},
            "doors": [],
            "objectZones": [
                {"id": "z1", "bounds": {"x": 0.0, "y": 0.0, "w": 0.4, "h": 0.4}}
            ],
        }
        pred = copy.deepcopy(gt)
        # Shift predicted zone right by half width (0.2)
        pred["objectZones"][0]["bounds"]["x"] = 0.2

        # Manually inject GT so scorer can find it
        scorer._ground_truths["test-iou"] = gt

        result = scorer.score_trial(json.dumps(pred), "test-iou")
        # Intersection = 0.2 * 0.4 = 0.08
        # Union = 0.4*0.4 + 0.4*0.4 - 0.08 = 0.24
        # IoU = 0.08 / 0.24 ≈ 0.333
        assert result.zone_coverage == pytest.approx(1 / 3, abs=0.01)


# ------------------------------------------------------------------
# 9. Spawn plausibility
# ------------------------------------------------------------------


class TestSpawnPlausibility:
    def test_spawn_in_walkable_zone(self, scorer, corridor_gt):
        """Spawn at centre of corridor-floor zone should be plausible."""
        pred = copy.deepcopy(corridor_gt)
        pred["spawnPoints"] = [
            {"id": "spawn-ok", "position": {"x": 0.50, "y": 0.78}, "purpose": "general"}
        ]
        result = scorer.score_trial(json.dumps(pred), "castle-corridor")
        assert result.spawn_plausibility == 1.0

    def test_spawn_at_origin_implausible(self, scorer, corridor_gt):
        """Spawn at (0,0) is outside all walkable zones and far from GT spawns."""
        pred = copy.deepcopy(corridor_gt)
        pred["spawnPoints"] = [
            {"id": "spawn-bad", "position": {"x": 0.0, "y": 0.0}, "purpose": "general"}
        ]
        result = scorer.score_trial(json.dumps(pred), "castle-corridor")
        assert result.spawn_plausibility == 0.0

    def test_no_spawns_gives_zero(self, scorer, corridor_gt):
        pred = copy.deepcopy(corridor_gt)
        pred["spawnPoints"] = []
        result = scorer.score_trial(json.dumps(pred), "castle-corridor")
        assert result.spawn_plausibility == 0.0
