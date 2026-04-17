import json
from pathlib import Path

import jsonschema
import pytest

from llm_eval.validator import SchemaValidator, ValidationResult

SCENE_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "SceneTemplate",
    "type": "object",
    "required": ["sceneId", "displayNameKey", "background", "doors"],
    "properties": {
        "sceneId": {"type": "string", "pattern": "^[a-z0-9-]+$"},
        "displayNameKey": {"type": "string"},
        "descriptionKey": {"type": "string"},
        "sceneType": {"enum": ["indoor", "outdoor"]},
        "background": {
            "type": "object",
            "required": ["assetPath", "width", "height"],
            "properties": {
                "assetPath": {"type": "string"},
                "width": {"type": "number", "minimum": 1},
                "height": {"type": "number", "minimum": 1},
            },
        },
        "doors": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "position", "size", "spawnPoint"],
                "properties": {
                    "id": {"type": "string", "pattern": "^door-[a-z0-9-]+$"},
                    "position": {"$ref": "#/$defs/point"},
                    "size": {"$ref": "#/$defs/size"},
                    "targetSceneId": {"type": "string"},
                    "targetDoorId": {"type": "string"},
                    "spawnPoint": {"$ref": "#/$defs/point"},
                    "spriteKey": {"type": "string"},
                    "interactionRadius": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                    },
                },
            },
        },
        "spawnPoints": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "position", "purpose"],
                "properties": {
                    "id": {"type": "string"},
                    "position": {"$ref": "#/$defs/point"},
                    "purpose": {"enum": ["initial", "chaos-button", "general"]},
                },
            },
        },
        "objectZones": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "bounds"],
                "properties": {
                    "id": {"type": "string"},
                    "bounds": {"$ref": "#/$defs/rect"},
                    "label": {"type": "string"},
                    "zIndex": {"type": "integer"},
                },
            },
        },
        "defaultObjects": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["objectId", "position"],
                "properties": {
                    "objectId": {"type": "string"},
                    "position": {"$ref": "#/$defs/point"},
                    "zIndex": {"type": "integer"},
                    "state": {"type": "string"},
                },
            },
        },
    },
    "$defs": {
        "point": {
            "type": "object",
            "required": ["x", "y"],
            "properties": {
                "x": {"type": "number", "minimum": 0, "maximum": 1},
                "y": {"type": "number", "minimum": 0, "maximum": 1},
            },
        },
        "size": {
            "type": "object",
            "required": ["w", "h"],
            "properties": {
                "w": {"type": "number", "minimum": 0, "maximum": 1},
                "h": {"type": "number", "minimum": 0, "maximum": 1},
            },
        },
        "rect": {
            "type": "object",
            "required": ["x", "y", "w", "h"],
            "properties": {
                "x": {"type": "number", "minimum": 0, "maximum": 1},
                "y": {"type": "number", "minimum": 0, "maximum": 1},
                "w": {"type": "number", "minimum": 0, "maximum": 1},
                "h": {"type": "number", "minimum": 0, "maximum": 1},
            },
        },
    },
}

VALID_TEMPLATE = {
    "sceneId": "test-scene",
    "displayNameKey": "scene_test",
    "background": {"assetPath": "test.svg", "width": 1920, "height": 1080},
    "doors": [
        {
            "id": "door-test",
            "position": {"x": 0.5, "y": 0.5},
            "size": {"w": 0.1, "h": 0.2},
            "spawnPoint": {"x": 0.55, "y": 0.7},
        }
    ],
}


@pytest.fixture()
def schema_path(tmp_path: Path) -> Path:
    path = tmp_path / "scene-template.schema.json"
    path.write_text(json.dumps(SCENE_SCHEMA))
    return path


@pytest.fixture()
def validator(schema_path: Path) -> SchemaValidator:
    return SchemaValidator(str(schema_path))


class TestSchemaValidatorInit:
    def test_loads_valid_schema(self, schema_path: Path) -> None:
        v = SchemaValidator(str(schema_path))
        assert v._schema == SCENE_SCHEMA

    def test_rejects_invalid_schema(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.schema.json"
        bad.write_text(json.dumps({"type": "not-a-real-type"}))
        with pytest.raises(jsonschema.SchemaError):
            SchemaValidator(str(bad))


class TestValidTemplate:
    def test_valid_template_passes(self, validator: SchemaValidator) -> None:
        result = validator.validate(json.dumps(VALID_TEMPLATE))
        assert result.valid is True
        assert result.errors == []
        assert result.parsed == VALID_TEMPLATE

    def test_valid_template_with_optional_fields(
        self, validator: SchemaValidator
    ) -> None:
        template = {
            **VALID_TEMPLATE,
            "descriptionKey": "scene_test_desc",
            "sceneType": "indoor",
        }
        result = validator.validate(json.dumps(template))
        assert result.valid is True


class TestMissingRequiredFields:
    @pytest.mark.parametrize(
        "missing_field", ["sceneId", "displayNameKey", "background", "doors"]
    )
    def test_missing_top_level_required_field(
        self, validator: SchemaValidator, missing_field: str
    ) -> None:
        template = {k: v for k, v in VALID_TEMPLATE.items() if k != missing_field}
        result = validator.validate(json.dumps(template))
        assert result.valid is False
        assert any(missing_field in e for e in result.errors)

    def test_missing_door_required_field(self, validator: SchemaValidator) -> None:
        template = {
            **VALID_TEMPLATE,
            "doors": [{"id": "door-test", "position": {"x": 0.5, "y": 0.5}}],
        }
        result = validator.validate(json.dumps(template))
        assert result.valid is False
        assert len(result.errors) > 0


class TestOutOfRangeCoordinates:
    def test_x_above_max(self, validator: SchemaValidator) -> None:
        template = {
            **VALID_TEMPLATE,
            "doors": [
                {
                    "id": "door-test",
                    "position": {"x": 1.5, "y": 0.5},
                    "size": {"w": 0.1, "h": 0.2},
                    "spawnPoint": {"x": 0.55, "y": 0.7},
                }
            ],
        }
        result = validator.validate(json.dumps(template))
        assert result.valid is False
        assert any("maximum" in e for e in result.errors)

    def test_y_below_min(self, validator: SchemaValidator) -> None:
        template = {
            **VALID_TEMPLATE,
            "doors": [
                {
                    "id": "door-test",
                    "position": {"x": 0.5, "y": -0.1},
                    "size": {"w": 0.1, "h": 0.2},
                    "spawnPoint": {"x": 0.55, "y": 0.7},
                }
            ],
        }
        result = validator.validate(json.dumps(template))
        assert result.valid is False
        assert any("minimum" in e for e in result.errors)

    def test_spawn_point_out_of_range(self, validator: SchemaValidator) -> None:
        template = {
            **VALID_TEMPLATE,
            "doors": [
                {
                    "id": "door-test",
                    "position": {"x": 0.5, "y": 0.5},
                    "size": {"w": 0.1, "h": 0.2},
                    "spawnPoint": {"x": 2.0, "y": 0.7},
                }
            ],
        }
        result = validator.validate(json.dumps(template))
        assert result.valid is False


class TestMalformedJson:
    def test_not_json_at_all(self, validator: SchemaValidator) -> None:
        result = validator.validate("this is not json {{{")
        assert result.valid is False
        assert result.parsed is None
        assert any("Invalid JSON" in e for e in result.errors)

    def test_truncated_json(self, validator: SchemaValidator) -> None:
        result = validator.validate('{"sceneId": "test-scene"')
        assert result.valid is False
        assert result.parsed is None

    def test_none_input(self, validator: SchemaValidator) -> None:
        result = validator.validate(None)  # type: ignore[arg-type]
        assert result.valid is False
        assert result.parsed is None
        assert any("Invalid JSON" in e for e in result.errors)


class TestEmptyString:
    def test_empty_string(self, validator: SchemaValidator) -> None:
        result = validator.validate("")
        assert result.valid is False
        assert result.parsed is None
        assert any("Invalid JSON" in e for e in result.errors)
