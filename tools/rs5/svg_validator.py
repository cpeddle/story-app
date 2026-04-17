from __future__ import annotations

from dataclasses import dataclass, field
from lxml import etree


@dataclass
class SVGValidationResult:
    valid_xml: bool = False
    has_background_group: bool = False
    has_doors_group: bool = False
    has_spawn_group: bool = False
    has_zones_group: bool = False
    doors_found: int = 0
    spawn_points_found: int = 0
    zones_found: int = 0
    coordinate_errors: list[str] = field(default_factory=list)
    overall_valid: bool = False


class SVGTemplateValidator:
    """Validates annotated SVG scene templates for RS-5 evaluation."""

    SVG_NS = "http://www.w3.org/2000/svg"
    VIEWBOX_WIDTH = 1920
    VIEWBOX_HEIGHT = 1080

    def validate(self, svg_str: str) -> SVGValidationResult:
        result = SVGValidationResult()

        # Parse XML
        try:
            root = etree.fromstring(svg_str.encode("utf-8") if isinstance(svg_str, str) else svg_str)
            result.valid_xml = True
        except etree.XMLSyntaxError:
            return result  # overall_valid stays False

        ns = {"svg": self.SVG_NS}

        # Check required groups
        bg = root.xpath(".//svg:g[@id='background'] | .//g[@id='background']", namespaces=ns)
        if not bg:
            bg = root.xpath(".//*[@id='background']")
        result.has_background_group = len(bg) > 0

        doors_group = root.xpath(".//svg:g[@id='doors'] | .//g[@id='doors']", namespaces=ns)
        if not doors_group:
            doors_group = root.xpath(".//*[@id='doors']")
        result.has_doors_group = len(doors_group) > 0

        spawn_group = root.xpath(".//svg:g[@id='spawn-points'] | .//g[@id='spawn-points']", namespaces=ns)
        if not spawn_group:
            spawn_group = root.xpath(".//*[@id='spawn-points']")
        result.has_spawn_group = len(spawn_group) > 0

        zones_group = root.xpath(".//svg:g[@id='object-zones'] | .//g[@id='object-zones']", namespaces=ns)
        if not zones_group:
            zones_group = root.xpath(".//*[@id='object-zones']")
        result.has_zones_group = len(zones_group) > 0

        # Extract and validate doors
        if result.has_doors_group:
            door_elems = doors_group[0].findall(".//{%s}rect" % self.SVG_NS)
            if not door_elems:
                door_elems = doors_group[0].findall(".//rect")
            result.doors_found = len(door_elems)
            for elem in door_elems:
                self._validate_rect_coords(elem, "door", result)
                # Check required data attributes
                for attr in ["data-spawn-x", "data-spawn-y"]:
                    val = elem.get(attr)
                    if val is not None:
                        try:
                            v = float(val)
                            if not (0 <= v <= self.VIEWBOX_WIDTH if "x" in attr else 0 <= v <= self.VIEWBOX_HEIGHT):
                                result.coordinate_errors.append(
                                    f"{elem.get('id', '?')}: {attr}={val} out of range"
                                )
                        except ValueError:
                            result.coordinate_errors.append(
                                f"{elem.get('id', '?')}: {attr}={val} is not a number"
                            )

        # Extract and validate spawn points
        if result.has_spawn_group:
            spawn_elems = spawn_group[0].findall(".//{%s}circle" % self.SVG_NS)
            if not spawn_elems:
                spawn_elems = spawn_group[0].findall(".//circle")
            result.spawn_points_found = len(spawn_elems)
            for elem in spawn_elems:
                self._validate_circle_coords(elem, "spawn", result)

        # Extract and validate zones
        if result.has_zones_group:
            zone_elems = zones_group[0].findall(".//{%s}rect" % self.SVG_NS)
            if not zone_elems:
                zone_elems = zones_group[0].findall(".//rect")
            result.zones_found = len(zone_elems)
            for elem in zone_elems:
                self._validate_rect_coords(elem, "zone", result)

        # Overall valid check
        result.overall_valid = (
            result.valid_xml
            and result.has_background_group
            and result.has_doors_group
            and result.has_spawn_group
            and result.has_zones_group
            and result.doors_found > 0
            and result.spawn_points_found > 0
            and result.zones_found > 0
            and len(result.coordinate_errors) == 0
        )

        return result

    def _validate_rect_coords(self, elem, prefix: str, result: SVGValidationResult) -> None:
        eid = elem.get("id", f"unknown-{prefix}")
        for attr, limit in [("x", self.VIEWBOX_WIDTH), ("y", self.VIEWBOX_HEIGHT),
                            ("width", self.VIEWBOX_WIDTH), ("height", self.VIEWBOX_HEIGHT)]:
            val = elem.get(attr)
            if val is not None:
                try:
                    v = float(val)
                    if v < 0 or v > limit:
                        result.coordinate_errors.append(f"{eid}: {attr}={val} out of range (0–{limit})")
                except ValueError:
                    result.coordinate_errors.append(f"{eid}: {attr}={val} is not a number")

    def _validate_circle_coords(self, elem, prefix: str, result: SVGValidationResult) -> None:
        eid = elem.get("id", f"unknown-{prefix}")
        for attr, limit in [("cx", self.VIEWBOX_WIDTH), ("cy", self.VIEWBOX_HEIGHT)]:
            val = elem.get(attr)
            if val is not None:
                try:
                    v = float(val)
                    if v < 0 or v > limit:
                        result.coordinate_errors.append(f"{eid}: {attr}={val} out of range (0–{limit})")
                except ValueError:
                    result.coordinate_errors.append(f"{eid}: {attr}={val} is not a number")
