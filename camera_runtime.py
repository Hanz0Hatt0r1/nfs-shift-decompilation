"""Evidence-backed camera configuration/runtime contracts from retail SHIFT.exe.

Phase 254 covers the loader and registration boundaries around:
  * FUN_00811160 (global CameraConfig loader)
  * FUN_00812650 (Trackside Cams / Splines / Areas registration)
  * FUN_008117c0 (camera element instantiation: class + id + data)
  * FUN_00811d40 (area element instantiation: class + id + data)
  * FUN_008127c0 (TrackCameraMan camera-file resolution)

The module deliberately keeps XML payloads raw. Camera math, class inheritance and
behavior are only exposed where the decompilation makes the contract explicit.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


FORMAT = "SHIFT.CameraRuntime/1"

CAMERA_CONFIG_PATH = r"Cameras\\CameraConfig.xml"
TRACKS_CAMERA_CONFIG_PATH = r"Tracks\\CameraConfig.xml"
TRACK_CAMERA_CONFIG_TEMPLATE = r"Tracks\\%s\\CameraConfig.xml"
LOCAL_CAMERAS_PATH = r"Cameras\\localCams.xml"
TRACK_CAMERA_TEMPLATE = r"Cameras\\%s.xml"

REGISTERED_GROUPS = {
    "trackside_cams": {"xml_group": "Trackside Cams", "this_offset": 0x14},
    "splines": {"xml_group": "Splines", "this_offset": 0x48},
    "areas": {"xml_group": "Areas", "this_offset": 0x7C},
}

STATIC_CAMERA_PROPERTIES = (
    {"name": "Name", "type_code": 0x00, "offset": 0x60, "registration": "FUN_008156b0"},
    {"name": "Pos", "type_code": 0x10, "offset": 0x20, "registration": "FUN_008156b0"},
    {"name": "QuatOri", "type_code": 0x19, "offset": 0x10, "registration": "FUN_008156b0"},
    {"name": "FOV", "type_code": 0x0A, "offset": 0x64, "registration": "FUN_008156b0"},
    {"name": "Type", "type_code": 0x03, "offset": 0x68, "registration": "FUN_008156b0"},
    {"name": "NearZ", "type_code": 0x0A, "offset": 0x6C, "registration": "FUN_008156b0"},
    {"name": "FarZ", "type_code": 0x0A, "offset": 0x70, "registration": "FUN_008156b0"},
    {"name": "Target", "type_code": 0x0D, "offset": 0x78, "registration": "FUN_008156b0"},
    {"name": "LookAt", "type_code": 0x0D, "offset": 0x80, "registration": "FUN_008156b0"},
    {"name": "TargetOffset", "type_code": 0x10, "offset": 0x84, "registration": "FUN_008156b0"},
    {"name": "LookAtOffset", "type_code": 0x10, "offset": 0x90, "registration": "FUN_008156b0"},
    {"name": "ProximityShakeFrequency", "type_code": 0x0A, "offset": 0x9C, "registration": "FUN_008156b0"},
    {"name": "ProximityShakeMagnitude", "type_code": 0x0A, "offset": 0xA0, "registration": "FUN_008156b0"},
    {"name": "ProximityShakeMinDistance", "type_code": 0x0A, "offset": 0xA4, "registration": "FUN_008156b0"},
    {"name": "ProximityShakeMaxDistance", "type_code": 0x0A, "offset": 0xA8, "registration": "FUN_008156b0"},
    {"name": "ProximityShakeMinSpeed", "type_code": 0x0A, "offset": 0xAC, "registration": "FUN_008156b0"},
    {"name": "ProximityShakeMaxSpeed", "type_code": 0x0A, "offset": 0xB0, "registration": "FUN_008156b0"},
    {"name": "ShakeFrequencyMin", "type_code": 0x0A, "offset": 0xB4, "registration": "FUN_008156b0"},
    {"name": "ShakeFrequency", "type_code": 0x0A, "offset": 0xB8, "registration": "FUN_008156b0"},
    {"name": "ShakeMagnitudeMin", "type_code": 0x0A, "offset": 0xBC, "registration": "FUN_008156b0"},
    {"name": "ShakeMagnitude", "type_code": 0x0A, "offset": 0xC0, "registration": "FUN_008156b0"},
    {"name": "ShakeScreenVelocityMin", "type_code": 0x0A, "offset": 0xB4, "registration": "FUN_008156b0"},
    {"name": "ShakeScreenVelocity", "type_code": 0x0A, "offset": 0xB8, "registration": "FUN_008156b0"},
    {"name": "SoundEffect", "type_code": 0x00, "offset": 0xCC, "registration": "FUN_008156b0"},
    {"name": "LODDistanceMultiplier", "type_code": 0x0A, "offset": 0xD0, "registration": "FUN_008156b0"},
    {"name": "OverridedBy", "type_code": 0x00, "offset": 0xD4, "registration": "FUN_008156b0"},
    {"name": "UserDataName", "type_code": 0x00, "offset": 0xDC, "registration": "FUN_008156b0"},
    {"name": "UserDataValue", "type_code": 0x0A, "offset": 0xE0, "registration": "FUN_008156b0"},
    {"name": "ActiveAreas", "type_code": 0x06, "offset": 0x2C, "registration": "FUN_008156b0"},
)

TRACKING_CAMERA_PROPERTIES = (
    {"name": "MovementRate", "type_code": 0x0A, "offset": 0xF0, "registration": "FUN_0081ebc0"},
    {"name": "TrackingRate", "type_code": 0x0A, "offset": 0xF4, "registration": "FUN_0081ebc0"},
    {"name": "SplineID", "type_code": 0x0D, "offset": 0xF8, "registration": "FUN_0081ebc0"},
    {"name": "TargetSplineID", "type_code": 0x0D, "offset": 0xFC, "registration": "FUN_0081ebc0"},
    {"name": "bAutoZoom", "type_code": 0x20, "offset": 0x100, "registration": "FUN_0081ebc0"},
    {"name": "bStaticDirection", "type_code": 0x20, "offset": 0x101, "registration": "FUN_0081ebc0"},
    {"name": "SplineChaseDir", "type_code": 0x0A, "offset": 0x104, "registration": "FUN_0081ebc0"},
    {"name": "TargetSplineChaseDir", "type_code": 0x0A, "offset": 0x108, "registration": "FUN_0081ebc0"},
    {"name": "TrackingLag", "type_code": 0x0A, "offset": 0x128, "registration": "FUN_0081ebc0"},
    {"name": "TrackingLagSmoothening", "type_code": 0x0A, "offset": 0x12C, "registration": "FUN_0081ebc0"},
    {"name": "TrackingErrorFrequency", "type_code": 0x0A, "offset": 0x130, "registration": "FUN_0081ebc0"},
    {"name": "TrackingErrorCorrectionSpeed", "type_code": 0x0A, "offset": 0x134, "registration": "FUN_0081ebc0"},
    {"name": "TrackingErrorMagnitude", "type_code": 0x0A, "offset": 0x138, "registration": "FUN_0081ebc0"},
    {"name": "SplinesRatio", "type_code": 0x0A, "offset": 0x13C, "registration": "FUN_0081ebc0"},
    {"name": "bSyncSplines", "type_code": 0x20, "offset": 0x140, "registration": "FUN_0081ebc0"},
    {"name": "OnSplineEndReached", "type_code": 0x0D, "offset": 0x144, "registration": "FUN_0081ebc0"},
    {"name": "OnTargetSplineEndReached", "type_code": 0x0D, "offset": 0x148, "registration": "FUN_0081ebc0"},
)

AREA_PROPERTY_REGISTRATIONS = (
    {
        "registration": "FUN_0081e780",
        "properties": (
            {"name": "Centre", "type_code": 0x10, "offset": 0x10},
            {"name": "Radius", "type_code": 0x01, "offset": 0x1C},
        ),
    },
    {
        "registration": "FUN_0081e880",
        "properties": (
            {"name": "XForm", "type_code": 0x1D, "offset": 0x10},
            {"name": "Dimensions", "type_code": 0x10, "offset": 0x50},
        ),
    },
)

# Proven class-object inheritance links recovered from the static initialization
# functions near FUN_00a8ced0..FUN_00a8d800. Links whose base object is not a
# camera-class symbol are intentionally omitted rather than guessed.
CAMERA_CLASS_BASES = {
    "CCameraView": "CBaseCamera",
    "CBaseCamera": "CCameraObj",
    "CFreeCamera": "CCameraObj",
    "CAttachedCamera": "CBaseCamera",
    "CStaticCamera": "CBaseCamera",
    "CTrackingCamera": "CStaticCamera",
    "CSphereArea": "CCamArea",
    "COBBArea": "CCamArea",
    "CTrackingCamData": "CStaticCamData",
}

# These classes point at the same non-camera base object DAT_00bfa608 in the
# executable's registration records. The class name for that base is not resolved
# by the current evidence, so chains terminating here remain partial.
UNRESOLVED_CAMERA_BASE_CLASSES = {
    "CStaticCamData",
    "CCamArea",
    "CCamSplineNode",
    "CCamSpline",
    "CCameraConfig",
    "CTrackCameraMan",
    "CCameraObj",
}

CAMERA_CLASS_REGISTRATIONS = {
    "CTrackCameraMan": "FUN_00a8ced0",
    "CStaticCamera": "FUN_00a8cf90",
    "CStaticCamData": "FUN_00a8d020",
    "CBaseCamera": "FUN_00a8d190",
    "CFreeCamera": "FUN_00a8d220",
    "CAttachedCamera": "FUN_00a8d2a0",
    "CCamArea": "FUN_00a8d370",
    "CSphereArea": "FUN_00a8d3f0",
    "COBBArea": "FUN_00a8d480",
    "CTrackingCamera": "FUN_00a8d510",
    "CTrackingCamData": "FUN_00a8d5a0",
    "CCamSplineNode": "FUN_00a8d650",
    "CCamSpline": "FUN_00a8d6e0",
    "CCameraConfig": "FUN_00a8d770",
    "CCameraObj": "FUN_00a8d800",
    "CCameraView": "FUN_00a8cdb0",
}

RUNTIME_CLASS_NAMES = (
    "CBaseCamera",
    "CCameraConfig",
    "CCameraEvent",
    "CCameraObj",
    "CCameraView",
    "CCamArea",
    "CCamSpline",
    "CCamSplineNode",
    "CFreeCamera",
    "CStaticCamData",
    "CStaticCamera",
    "CTrackingCamData",
    "CTrackingCamera",
    "CTrackCameraMan",
)


@dataclass(frozen=True)
class CameraLoadPlan:
    """Ordered file-loading edges recovered from FUN_00811160/FUN_008127c0."""

    global_paths: tuple[str, ...]
    track_camera_paths: tuple[str, ...]
    local_paths: tuple[str, ...] = (LOCAL_CAMERAS_PATH,)

    def as_dict(self) -> dict[str, Any]:
        return {
            "format": FORMAT,
            "version": 1,
            "global_paths": list(self.global_paths),
            "track_camera_paths": list(self.track_camera_paths),
            "local_paths": list(self.local_paths),
            "evidence": {
                "global_loader": "FUN_00811160",
                "camera_file_loader": "FUN_008127c0",
                "local_camera_loader": "FUN_008127c0",
            },
        }


def build_camera_load_plan(*, track_name: str | None = None, camera_name: str | None = None) -> CameraLoadPlan:
    """Build source-observed path candidates without deciding which file exists.

    FUN_00811160 loads Cameras\\CameraConfig.xml, then either the global
    Tracks\\CameraConfig.xml or track-specific Tracks\\<track>\\CameraConfig.xml.

    FUN_008127c0 later loads Cameras\\localCams.xml and, for a named camera,
    first tries the supplied path followed by Cameras\\<name>.xml.
    """
    track_name = (track_name or "").strip()
    camera_name = (camera_name or "").strip()

    global_paths = [CAMERA_CONFIG_PATH]
    global_paths.append(
        TRACKS_CAMERA_CONFIG_PATH
        if not track_name
        else TRACK_CAMERA_CONFIG_TEMPLATE % track_name
    )

    track_camera_paths = (
        [camera_name, TRACK_CAMERA_TEMPLATE % camera_name]
        if camera_name
        else [TRACK_CAMERA_TEMPLATE % ""]
    )
    return CameraLoadPlan(tuple(global_paths), tuple(track_camera_paths))


def _text_or_none(element: ET.Element) -> str | None:
    text = element.text.strip() if element.text else ""
    return text or None


def _element_record(element: ET.Element, parent_path: str) -> dict[str, Any]:
    data_node = next(
        (child for child in list(element) if child.tag.lower().split("}")[-1] == "data"),
        None,
    )
    record: dict[str, Any] = {
        "tag": element.tag,
        "path": parent_path,
        "class": element.attrib.get("class"),
        "id": element.attrib.get("id"),
        "attributes": dict(element.attrib),
        "data_attributes": dict(data_node.attrib) if data_node is not None else {},
        "data_children": {},
    }
    if data_node is not None:
        for child in list(data_node):
            key = child.tag.split("}")[-1]
            if child.attrib:
                record["data_children"][key] = {
                    "attributes": dict(child.attrib),
                    "text": _text_or_none(child),
                }
            else:
                record["data_children"][key] = _text_or_none(child)
    return record


def parse_camera_xml(data: str | bytes, *, source_name: str = "<memory>") -> dict[str, Any]:
    """Parse camera XML while retaining unknown fields verbatim.

    The runtime handlers fetch the elements container, read class + id, and pass
    each data node into a reflected object constructor. This mirrors that boundary
    without applying class inheritance or camera math.
    """
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        raise ValueError(f"invalid camera XML: {exc}") from exc

    objects: list[dict[str, Any]] = []
    elements_nodes = [
        node
        for node in root.iter()
        if node.tag.split("}")[-1].lower() == "elements"
    ]
    search_roots = elements_nodes or [root]

    for search_root in search_roots:
        for index, element in enumerate(list(search_root)):
            if "class" not in element.attrib and "id" not in element.attrib:
                continue
            objects.append(_element_record(
                element,
                f"/{search_root.tag.split('}')[-1]}[{index}]",
            ))

    return {
        "format": FORMAT,
        "version": 1,
        "source": {"name": source_name},
        "root_tag": root.tag,
        "object_count": len(objects),
        "objects": objects,
        "class_hierarchy": [resolve_camera_class_chain(row["class"]) for row in objects if row.get("class")],
        "runtime_boundary": {
            "elements_container": "elements",
            "required_attributes": ["class", "id"],
            "data_container": "data",
            "registration": {
                "trackside_cams": "FUN_00812260",
                "splines": "FUN_00812450",
                "areas": "FUN_00812550",
                "camera_object_factory": "FUN_008117c0",
                "area_object_factory": "FUN_00811d40",
            },
        },
        "limitations": [
            "class inheritance resolution is limited to the proven camera-class prefix exported by resolve_camera_class_chain()",
            "camera behavior and transforms are not synthesized from XML values",
            "the executable type_code numbers are retained but not turned into a new ABI",
        ],
    }


def resolve_camera_class_chain(class_name: str, *, max_depth: int = 32) -> dict[str, Any]:
    """Resolve the proven prefix of a camera/area class inheritance chain."""
    if max_depth <= 0:
        raise ValueError("max_depth must be positive")
    current = str(class_name)
    chain = [current]
    seen = {current}
    cycle = False
    for _ in range(max_depth - 1):
        base = CAMERA_CLASS_BASES.get(current)
        if base is None:
            break
        if base in seen:
            cycle = True
            break
        chain.append(base)
        seen.add(base)
        current = base
    return {
        "class_name": str(class_name),
        "chain": chain,
        "resolved_links": max(0, len(chain) - 1),
        "terminated_at": chain[-1],
        "fully_resolved": not cycle and chain[-1] not in CAMERA_CLASS_BASES and chain[-1] not in UNRESOLVED_CAMERA_BASE_CLASSES,
        "cycle": cycle,
        "evidence": {
            "resolver": "FUN_006408f0",
            "class_initializers": dict(CAMERA_CLASS_REGISTRATIONS),
        },
    }


def property_catalog() -> dict[str, Any]:
    """Return the source registration tables used by Phase 254 tooling."""
    return {
        "format": FORMAT,
        "version": 1,
        "static_camera": list(STATIC_CAMERA_PROPERTIES),
        "tracking_camera": list(TRACKING_CAMERA_PROPERTIES),
        "area_registrations": [
            {"registration": row["registration"], "properties": list(row["properties"])}
            for row in AREA_PROPERTY_REGISTRATIONS
        ],
        "runtime_class_names": list(RUNTIME_CLASS_NAMES),
        "camera_class_bases": dict(CAMERA_CLASS_BASES),
        "camera_class_registrations": dict(CAMERA_CLASS_REGISTRATIONS),
        "unresolved_camera_base_classes": sorted(UNRESOLVED_CAMERA_BASE_CLASSES),
        "evidence": {
            "static_camera_data_registration": "FUN_008156b0",
            "tracking_camera_data_registration": "FUN_0081ebc0",
            "area_registration_a": "FUN_0081e780",
            "area_registration_b": "FUN_0081e880",
            "group_registration": "FUN_00812650",
        },
    }


def dump_json(report: dict[str, Any], path: str | Path) -> None:
    Path(path).write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
