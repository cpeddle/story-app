from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure the rs5 package root is importable when running pytest from any directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from svg_validator import SVGTemplateValidator, SVGValidationResult

VALID_SVG = """\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 1080">
  <g id="background"><rect x="0" y="0" width="1920" height="1080" fill="#eee"/></g>
  <g id="doors">
    <rect id="door-main" x="100" y="400" width="80" height="200"
          data-target-scene="corridor" data-target-door="door-exit"
          data-spawn-x="150" data-spawn-y="700"/>
  </g>
  <g id="spawn-points">
    <circle id="spawn-center" cx="960" cy="800" r="10" data-purpose="initial"/>
  </g>
  <g id="object-zones">
    <rect id="zone-table" x="500" y="600" width="200" height="100"
          data-label="table" data-z-index="5"/>
  </g>
</svg>"""


@pytest.fixture
def validator() -> SVGTemplateValidator:
    return SVGTemplateValidator()


class TestValidSVG:
    def test_overall_valid(self, validator: SVGTemplateValidator) -> None:
        result = validator.validate(VALID_SVG)
        assert result.overall_valid is True

    def test_all_groups_found(self, validator: SVGTemplateValidator) -> None:
        result = validator.validate(VALID_SVG)
        assert result.has_background_group is True
        assert result.has_doors_group is True
        assert result.has_spawn_group is True
        assert result.has_zones_group is True

    def test_element_counts(self, validator: SVGTemplateValidator) -> None:
        result = validator.validate(VALID_SVG)
        assert result.doors_found == 1
        assert result.spawn_points_found == 1
        assert result.zones_found == 1

    def test_no_coordinate_errors(self, validator: SVGTemplateValidator) -> None:
        result = validator.validate(VALID_SVG)
        assert result.coordinate_errors == []


class TestInvalidXML:
    def test_malformed_xml(self, validator: SVGTemplateValidator) -> None:
        result = validator.validate("<svg><g id='background'><unclosed>")
        assert result.valid_xml is False
        assert result.overall_valid is False

    def test_completely_broken(self, validator: SVGTemplateValidator) -> None:
        result = validator.validate("this is not xml at all")
        assert result.valid_xml is False
        assert result.overall_valid is False


class TestMissingGroups:
    def test_missing_doors_group(self, validator: SVGTemplateValidator) -> None:
        svg = """\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 1080">
  <g id="background"><rect x="0" y="0" width="1920" height="1080" fill="#eee"/></g>
  <g id="spawn-points">
    <circle id="spawn-center" cx="960" cy="800" r="10" data-purpose="initial"/>
  </g>
  <g id="object-zones">
    <rect id="zone-table" x="500" y="600" width="200" height="100"
          data-label="table" data-z-index="5"/>
  </g>
</svg>"""
        result = validator.validate(svg)
        assert result.has_doors_group is False
        assert result.overall_valid is False

    def test_missing_spawn_group(self, validator: SVGTemplateValidator) -> None:
        svg = """\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 1080">
  <g id="background"><rect x="0" y="0" width="1920" height="1080" fill="#eee"/></g>
  <g id="doors">
    <rect id="door-main" x="100" y="400" width="80" height="200"
          data-target-scene="corridor" data-target-door="door-exit"
          data-spawn-x="150" data-spawn-y="700"/>
  </g>
  <g id="object-zones">
    <rect id="zone-table" x="500" y="600" width="200" height="100"
          data-label="table" data-z-index="5"/>
  </g>
</svg>"""
        result = validator.validate(svg)
        assert result.has_spawn_group is False
        assert result.overall_valid is False


class TestOutOfRangeCoordinates:
    def test_x_exceeds_viewbox(self, validator: SVGTemplateValidator) -> None:
        svg = """\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 1080">
  <g id="background"><rect x="0" y="0" width="1920" height="1080" fill="#eee"/></g>
  <g id="doors">
    <rect id="door-main" x="2000" y="400" width="80" height="200"
          data-target-scene="corridor" data-target-door="door-exit"
          data-spawn-x="150" data-spawn-y="700"/>
  </g>
  <g id="spawn-points">
    <circle id="spawn-center" cx="960" cy="800" r="10" data-purpose="initial"/>
  </g>
  <g id="object-zones">
    <rect id="zone-table" x="500" y="600" width="200" height="100"
          data-label="table" data-z-index="5"/>
  </g>
</svg>"""
        result = validator.validate(svg)
        assert len(result.coordinate_errors) > 0
        assert any("door-main" in e and "x=" in e for e in result.coordinate_errors)
        assert result.overall_valid is False

    def test_negative_coordinate(self, validator: SVGTemplateValidator) -> None:
        svg = """\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 1080">
  <g id="background"><rect x="0" y="0" width="1920" height="1080" fill="#eee"/></g>
  <g id="doors">
    <rect id="door-main" x="100" y="400" width="80" height="200"
          data-target-scene="corridor" data-target-door="door-exit"
          data-spawn-x="150" data-spawn-y="700"/>
  </g>
  <g id="spawn-points">
    <circle id="spawn-center" cx="-10" cy="800" r="10" data-purpose="initial"/>
  </g>
  <g id="object-zones">
    <rect id="zone-table" x="500" y="600" width="200" height="100"
          data-label="table" data-z-index="5"/>
  </g>
</svg>"""
        result = validator.validate(svg)
        assert len(result.coordinate_errors) > 0
        assert any("spawn-center" in e for e in result.coordinate_errors)
        assert result.overall_valid is False


class TestDoorsNoSpawns:
    def test_doors_present_but_no_spawn_circles(self, validator: SVGTemplateValidator) -> None:
        svg = """\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 1080">
  <g id="background"><rect x="0" y="0" width="1920" height="1080" fill="#eee"/></g>
  <g id="doors">
    <rect id="door-main" x="100" y="400" width="80" height="200"
          data-target-scene="corridor" data-target-door="door-exit"
          data-spawn-x="150" data-spawn-y="700"/>
  </g>
  <g id="spawn-points"/>
  <g id="object-zones">
    <rect id="zone-table" x="500" y="600" width="200" height="100"
          data-label="table" data-z-index="5"/>
  </g>
</svg>"""
        result = validator.validate(svg)
        assert result.has_spawn_group is True
        assert result.spawn_points_found == 0
        assert result.overall_valid is False


class TestEmptySVG:
    def test_empty_svg_element(self, validator: SVGTemplateValidator) -> None:
        svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 1080"></svg>'
        result = validator.validate(svg)
        assert result.valid_xml is True
        assert result.has_background_group is False
        assert result.overall_valid is False

    def test_groups_present_but_no_children(self, validator: SVGTemplateValidator) -> None:
        svg = """\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 1080">
  <g id="background"/>
  <g id="doors"/>
  <g id="spawn-points"/>
  <g id="object-zones"/>
</svg>"""
        result = validator.validate(svg)
        assert result.valid_xml is True
        assert result.has_background_group is True
        assert result.doors_found == 0
        assert result.overall_valid is False
