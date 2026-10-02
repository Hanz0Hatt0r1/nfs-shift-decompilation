import importlib.util
import json
import sys
from pathlib import Path


def _load_module():
    tool_dir = Path(__file__).resolve().parents[1] / "tools" / "shift_live_dump"
    sys.path.insert(0, str(tool_dir))
    path = tool_dir / "audit_shift_class_candidates.py"
    spec = importlib.util.spec_from_file_location("audit_shift_class_candidates", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _manifest():
    ready_fields = [
        {
            "field_name": "value",
            "type_code": 1,
            "offset": 0x10,
            "flags": 0,
        }
    ]
    return {
        "source": "SHIFT.exe.c",
        "source_sha256": "source",
        "exe": "SHIFT.exe",
        "exe_sha256": "exe",
        "classes": [
            {
                "name": "Ready",
                "descriptor": 0x1000,
                "parent_class": None,
                "ancestry": [],
                "reflection_metadata_symbol": "DAT_2000",
                "reflection_functions": ["FUN_3000"],
                "field_count": 1,
                "resolved_field_name_count": 1,
                "static_field_offset_count": 1,
                "rtti_getter_addresses": [0x4000],
                "vtable_candidates": [0x5000],
                "unique_vtable": 0x5000,
                "fields": ready_fields,
            },
            {
                "name": "Blocked",
                "descriptor": 0x1100,
                "parent_class": None,
                "ancestry": [],
                "reflection_metadata_symbol": "DAT_2100",
                "reflection_functions": ["FUN_3100"],
                "field_count": 1,
                "resolved_field_name_count": 1,
                "static_field_offset_count": 0,
                "rtti_getter_addresses": [0x4100],
                "vtable_candidates": [0x5100],
                "unique_vtable": 0x5100,
                "fields": [
                    {
                        "field_name": "dynamic",
                        "type_code": 1,
                        "offset": None,
                        "flags": 0,
                    }
                ],
            },
        ],
    }


def test_initializer_evidence_annotates_without_changing_structural_gate(tmp_path):
    module = _load_module()
    module.build_manifest = lambda source, exe: _manifest()

    links = tmp_path / "initializer_links.json"
    links.write_text(
        json.dumps(
            {
                "format": module.INITIALIZER_FORMAT,
                "links": [
                    {
                        "class": "Ready",
                        "descriptor": 0x1000,
                        "factory_function": "FUN_6000",
                        "initializer_candidate": "FUN_7000",
                        "ghidra_direct_call": True,
                    },
                    {
                        "class": "Blocked",
                        "descriptor": 0x1100,
                        "factory_function": "FUN_6100",
                        "initializer_candidate": "FUN_7100",
                        "ghidra_direct_call": None,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    report = module.audit_candidates(Path("SHIFT.exe.c"), Path("SHIFT.exe"), links)
    assert report["structural_ready_count"] == 1
    assert report["blocked_count"] == 1
    assert report["initializer_linked_count"] == 2
    assert report["initializer_ghidra_confirmed_count"] == 1
    assert report["initializer_ghidra_mismatch_count"] == 0

    rows = {row["class_name"]: row for row in report["candidates"]}
    ready = rows["Ready"]
    blocked = rows["Blocked"]
    assert ready["structural_ready"] is True
    assert ready["initializer_linked"] is True
    assert ready["unambiguous_initializer"] == "FUN_7000"
    assert ready["initializer_ghidra_confirmed"] is True

    # Initializer evidence is orthogonal to the pre-existing structural gate.
    assert blocked["structural_ready"] is False
    assert blocked["blockers"] == ["dynamic_field_offsets"]
    assert blocked["initializer_linked"] is True
    assert blocked["initializer_ghidra_confirmed"] is None

    selected = module._select(report, [], [], False, False, True, None)
    assert {row["class_name"] for row in selected} == {"Ready", "Blocked"}


def test_initializer_ghidra_mismatch_is_preserved(tmp_path):
    module = _load_module()
    module.build_manifest = lambda source, exe: _manifest()
    links = tmp_path / "initializer_links.json"
    links.write_text(
        json.dumps(
            {
                "format": module.INITIALIZER_FORMAT,
                "links": [
                    {
                        "class": "Ready",
                        "descriptor": 0x1000,
                        "factory_function": "FUN_6000",
                        "initializer_candidate": "FUN_7000",
                        "ghidra_direct_call": False,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    report = module.audit_candidates(Path("SHIFT.exe.c"), Path("SHIFT.exe"), links)
    assert report["initializer_linked_count"] == 1
    assert report["initializer_ghidra_confirmed_count"] == 0
    assert report["initializer_ghidra_mismatch_count"] == 1
    ready = next(row for row in report["candidates"] if row["class_name"] == "Ready")
    assert ready["initializer_ghidra_confirmed"] is False
    assert ready["structural_ready"] is True
