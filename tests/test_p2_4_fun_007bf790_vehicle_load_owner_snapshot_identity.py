import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/p2_4_fun_007bf790_vehicle_load_owner_snapshot_identity.json"
HEADER = ROOT / "native_runtime/include/shift_fun_007bf790_vehicle_load_owner_snapshot_identity.hpp"
CPP = ROOT / "native_runtime/tests/fun_007bf790_vehicle_load_owner_snapshot_identity_check.cpp"
UPSTREAM = ROOT / "evidence/p2_4_fun_007bf790_vehicle_load_data_caster_binding.json"


def test_owner_snapshot_provenance_matches_existing_binding() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    upstream = json.loads(UPSTREAM.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.Fun007bf790VehicleLoadOwnerSnapshotIdentity/1"
    assert payload["source"]["caster_snapshot_contract"] == upstream["format"]
    assert payload["geometry"]["pointer_field_offset"] == upstream["owner_provenance"]["vehicle_load_data_pointer_offset"]
    assert payload["geometry"]["load_data_allocation_size"] == upstream["owner_provenance"]["allocation_size"]
    assert payload["geometry"]["caster_minimum_snapshot_size"] == upstream["caster_layout"]["minimum_snapshot_size"]
    assert payload["source"]["retail_executable_sha256"] == upstream["source"]["retail_executable_sha256"]


def test_owner_snapshot_keeps_lifetime_fail_closed() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    limits = payload["limits"]
    assert limits["actual_retail_pointer_dereference_internalized"] is False
    assert limits["snapshot_to_pointer_address_association_proven_by_native_runtime"] is False
    assert limits["VehicleLoadData_snapshot_lifetime_internalized"] is False
    assert limits["FUN_007584f0_computed_payloads_complete"] is False
    assert limits["complete_FUN_00765c40_internalized"] is False
    assert limits["top_level_provider_removed"] is False
    assert limits["external_provider_count_after"] == 7
    header = HEADER.read_text(encoding="utf-8")
    for token in ("0x66b4u", "kVehicleLoadDataAllocationSize",
                  "supplied_load_data_address", "address !=",
                  "materialize_fun_007bf790_caster_records"):
        assert token in header
    assert "reinterpret_cast" not in header


def test_owner_snapshot_cpp_check_compiles_and_runs(tmp_path: Path) -> None:
    compiler = shutil.which("c++") or shutil.which("g++")
    if compiler is None:
        pytest.skip("C++ compiler unavailable")
    binary = tmp_path / "fun_007bf790_vehicle_load_owner_snapshot_identity_check"
    subprocess.run([
        compiler, "-std=c++17", "-Wall", "-Wextra", "-Wpedantic",
        "-I", str(ROOT / "native_runtime/include"),
        str(CPP), "-o", str(binary),
    ], check=True, cwd=ROOT)
    completed = subprocess.run([str(binary)], check=True, cwd=ROOT,
                               text=True, capture_output=True)
    output = json.loads(completed.stdout)
    assert output["format"] == "SHIFT.Fun007bf790VehicleLoadOwnerSnapshotIdentity/1"
    assert output["owner_pointer_identity_checked"] is True
    assert output["left_right_caster_materialized"] is True
    assert output["snapshot_lifetime_owned"] is False
    assert output["external_provider_count"] == 7
