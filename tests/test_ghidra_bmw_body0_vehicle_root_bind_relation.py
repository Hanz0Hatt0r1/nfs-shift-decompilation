import importlib.util
import json
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "ghidra" / "build_bmw_body0_vehicle_root_bind_relation.py"
spec = importlib.util.spec_from_file_location("body0_vehicle_root_bind", MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


def _write_export(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "binary.json").write_text(json.dumps({
        "program_name": mod.PROGRAM,
        "executable_md5": mod.PE_MD5,
    }), encoding="utf-8")
    with (root / "functions.jsonl").open("w", encoding="utf-8") as handle:
        for address, (name, size, cc, fingerprint, _role) in mod.TARGETS.items():
            handle.write(json.dumps({
                "address": address,
                "name": name,
                "size": size,
                "calling_convention": cc,
                "mnemonic_sha256": fingerprint,
                "external": False,
                "thunk": False,
            }) + "\n")
    with (root / "callgraph.jsonl").open("w", encoding="utf-8") as handle:
        for source, instruction, target in mod.REQUIRED_DIRECT_EDGES:
            handle.write(json.dumps({
                "from_function": source,
                "instruction": instruction,
                "to": target,
                "indirect": False,
            }) + "\n")


def test_symbolic_relation_closes_only_outer_vehicle_root(tmp_path: Path) -> None:
    export = tmp_path / "export"
    _write_export(export)
    report = mod.build_bmw_body0_vehicle_root_bind_relation(export)

    assert report["format"] == "SHIFT.BMWBody0VehicleRootBindRelation/1"
    relation = report["symbolic_bind_relation"]
    assert relation["rotation"] == "identity"
    assert relation["translation"] == [
        "-HDVehicle[0x33b0]", "-HDVehicle[0x33b8]", "-HDVehicle[0x33c0]"
    ]
    assert relation["row_vector_matrix"][12:15] == relation["translation"]

    gates = report["gates"]
    assert gates["retail_vehicle_transform_to_HDVehicle_spawn_bridge_ready"] is True
    assert gates["BODY0_to_outer_vehicle_root_symbolic_matrix_ready"] is True
    assert gates["BMW_numeric_offset33b_ready"] is False
    assert gates["outer_vehicle_root_to_VHF_vehicle_root_ready"] is False
    assert gates["BODY0_bind_frame_proof_ready"] is False
    assert gates["vehicle_world_transform_ready"] is False
    assert report["scope"]["identity_translation_assumed"] is False
    assert report["scope"]["outer_vehicle_root_equated_to_VHF_root"] is False


def test_fingerprint_drift_fails_closed(tmp_path: Path) -> None:
    export = tmp_path / "export"
    _write_export(export)
    rows = [json.loads(line) for line in (export / "functions.jsonl").read_text().splitlines()]
    rows[0]["mnemonic_sha256"] = "0" * 64
    (export / "functions.jsonl").write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    try:
        mod.build_bmw_body0_vehicle_root_bind_relation(export)
    except ValueError as exc:
        assert "mnemonic fingerprint drift" in str(exc)
    else:
        raise AssertionError("fingerprint drift must fail closed")


def test_missing_retail_call_edge_fails_closed(tmp_path: Path) -> None:
    export = tmp_path / "export"
    _write_export(export)
    lines = (export / "callgraph.jsonl").read_text().splitlines()
    (export / "callgraph.jsonl").write_text("\n".join(lines[1:]) + "\n")
    try:
        mod.build_bmw_body0_vehicle_root_bind_relation(export)
    except ValueError as exc:
        assert "missing required direct call edge" in str(exc)
    else:
        raise AssertionError("missing retail edge must fail closed")
