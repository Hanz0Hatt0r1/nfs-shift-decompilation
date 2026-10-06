#!/usr/bin/env python3
from __future__ import annotations

import argparse, hashlib, json, struct
from pathlib import Path
from typing import Any, Mapping, Sequence

FORMAT = "SHIFT.BMWPrimaryPlayerFirstBootstrapRenderRootDelta/1"
RELATION_FORMAT = "SHIFT.OuterVehicleBMWVHFRootRelation/1"
SESSION_FORMAT = "SHIFT.BMWOffset33bNativeSessionSelection/1"
PE_MD5 = "705af8b420e5eb1e3834ac43d5533c6b"
SOURCE_SHA256 = "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"
VEHICLE = "BMW_M3_E36"
SESSION = "Silverstone+BMW_M3_E36"
SESSION_TARGET = SESSION
CANONICAL_VHF = "vehicles/bmw_m3_e36/bmw_m3_e36.vhf"
ORIGIN_GLOBALS = (0x00C16AB0, 0x00C16AB8, 0x00C16AC0)
FUNCTIONS = {
    "0x0074ddc3": ("FUN_0074ddc3", 957, "__fastcall", "1b8f7a6602190fdd97b5a3d410495c8ff92b3a8b854a703459427b1ff548e4a6"),
    "0x0074e760": ("FUN_0074e760", 101, "__fastcall", "ee0a3baf733559a20dd134f43707056898cf73dd31be7d15a51922e1c02260b4"),
    "0x0078ef00": ("FUN_0078ef00", 1538, "__fastcall", "f981daa8164768121875faef1a053d93a6f78e6a3901a73aa32904b875ddb8e1"),
    "0x00795d60": ("FUN_00795d60", 8797, "__fastcall", "c587cae5d3d8f99afed40fe0c059c8c60bc9cc45d9ee644f5e90e2e1f5a8eb14"),
    "0x00797fd0": ("FUN_00797fd0", 612, "__thiscall", "b8f3cb6525e0742e2afefd31ca51dd050a9d869444526ce03df41067ecb3eeb8"),
    "0x00798df0": ("FUN_00798df0", 1581, "__thiscall", "88904019443d1ea4edaf5a3ef40dd5abfe9e28109ab0b1f09296388f36026e16"),
    "0x0079bfd0": ("FUN_0079bfd0", 445, "__fastcall", "06e730897a4a85d93a5f33765fd15b0c52708fb2c864c290804024b109a3d950"),
}
EXPECTED_INCOMING = {
    "0x0079bfd0": {("0x0079c1c0", "0x0079c1e1")},
    "0x00798df0": {("0x0074ddc3", "0x0074de12")},
    "0x00795d60": {("0x00798df0", "0x007990ed")},
    "0x0078ef00": {("0x0074bfd0", "0x0074c05b"), ("0x00794a30", "0x00794a81"), ("0x0079b2d0", "0x0079b323")},
}

def req(ok: bool, msg: str) -> None:
    if not ok: raise ValueError(msg)

def obj(value: Any, label: str) -> Mapping[str, Any]:
    req(isinstance(value, Mapping), f"{label} missing")
    return value

def load_json(path: Path) -> Mapping[str, Any]:
    return obj(json.loads(path.read_text(encoding="utf-8")), str(path))

def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

def body(source: str, name: str) -> str:
    start = source.find(name + "(")
    while start >= 0:
        brace, semi = source.find("{", start), source.find(";", start)
        if brace >= 0 and (semi < 0 or brace < semi):
            depth = 0
            for i in range(brace, len(source)):
                depth += source[i] == "{"
                depth -= source[i] == "}"
                if depth == 0: return source[start:i + 1]
        start = source.find(name + "(", start + len(name) + 1)
    raise ValueError(f"{name} definition missing")

def validate_functions(rows: Sequence[Mapping[str, Any]]) -> None:
    selected = {str(r.get("address") or "").lower(): r for r in rows if str(r.get("address") or "").lower() in FUNCTIONS}
    req(set(selected) == set(FUNCTIONS), "required retail function fingerprint row missing")
    for address, expected in FUNCTIONS.items():
        r = selected[address]
        req((r.get("name"), r.get("size"), r.get("calling_convention"), r.get("mnemonic_sha256")) == expected, f"{address} fingerprint drift")

def validate_calls(rows: Sequence[Mapping[str, Any]]) -> dict[str, list[dict[str, str]]]:
    out = {}
    for target, expected in EXPECTED_INCOMING.items():
        actual = {(str(r.get("from_function") or "").lower(), str(r.get("instruction") or "").lower()) for r in rows if str(r.get("to") or "").lower() == target and r.get("indirect") is False}
        req(actual == expected, f"incoming direct-call set drift for {target}: {sorted(actual)}")
        out[target] = [{"from_function": a, "instruction": b} for a, b in sorted(actual)]
    return out

def validate_source(source: str, *, require_hash: bool = True) -> dict[str, Any]:
    if require_hash:
        req(hashlib.sha256(source.encode()).hexdigest() == SOURCE_SHA256, "retail decompiler source SHA-256 drift")
    restart, role, init = body(source, "FUN_0074ddc3"), body(source, "FUN_00797fd0"), body(source, "FUN_00798df0")
    ctor, delta, cfg, writer = body(source, "FUN_0079bfd0"), body(source, "FUN_00795d60"), body(source, "FUN_0074e760"), body(source, "FUN_0078ef00")
    markers = [
        "FUN_00797fd0((void *)(*unaff_ESI + 0x340),*(int *)(iVar1 + 0x10),'\\0',1);",
        "if (*(int *)(iVar1 + 0x10) == 0)", "DAT_00c10b34 = unaff_ESI;",
        "FUN_00798df0((void *)(iVar6 + 0x340),(char)*(undefined4 *)(unaff_EBP + 0xc));",
    ]
    for m in markers: req(m in restart, f"Restart marker drift: {m}")
    req([restart.index(m) for m in markers] == sorted(restart.index(m) for m in markers), "Restart role/InitVehicle order drift")
    req("FUN_0078ef00(" not in restart[:restart.index(markers[-1])], "origin writer entered Restart->InitVehicle prefix")
    req("*(int *)((int)this + 0x234) = param_1;" in role, "Vehicle+0x234 role store drift")
    req("*(undefined4 *)(param_1 + 0x10) = 0;" in cfg, "spawn config role default drift")
    for i in (0x67, 0x68, 0x69): req(f"param_1[0x{i:x}] = 0;" in ctor, f"constructor delta zero 0x{i:x} missing")
    call = "FUN_00795d60(this,param_1,local_2390,*(void **)((int)this + 0x1d00),param_1);"
    req(call in init and "FUN_0078ef00(" not in init[:init.index(call)], "InitVehicle delta prefix drift")
    for m in (
        "if (*(int *)((int)param_1 + 0x234) == 0)",
        "local_3c = local_28 - (float)_DAT_00c16ab0;",
        "local_38 = *(float *)((int)param_1 + 0x1a0) - (float)_DAT_00c16ab8;",
        "local_34 = *(float *)((int)param_1 + 0x1a4) - (float)_DAT_00c16ac0;",
        "*(float *)((int)param_1 + 0x19c) = local_3c;",
        "*(float *)((int)param_1 + 0x1a0) = local_38;",
        "*(float *)((int)param_1 + 0x1a4) = local_34;",
    ): req(m in delta, f"primary-role delta marker drift: {m}")
    req("(double *)&DAT_00c16ab0" in writer and "FUN_007afd20" in writer, "origin writer drift")
    if require_hash:
        req(source.count("FUN_0078ef00(") == 4, "origin writer source-call count drift")
    return {"role_field": "+0x234", "constructor_delta_zero": ["+0x19c", "+0x1a0", "+0x1a4"], "formula": "new_delta = old_delta - origin", "origin_writer": "FUN_0078ef00"}

def pe_zero_fill(image: bytes, va: int) -> dict[str, Any]:
    pe = struct.unpack_from("<I", image, 0x3c)[0]; req(image[pe:pe+4] == b"PE\0\0", "PE signature drift")
    n = struct.unpack_from("<H", image, pe+6)[0]; opt_size = struct.unpack_from("<H", image, pe+20)[0]; opt = pe+24
    base = struct.unpack_from("<I", image, opt+28)[0]; table = opt+opt_size; rva = va-base
    for i in range(n):
        off = table+i*40; name = image[off:off+8].split(b"\0",1)[0].decode()
        vsize, vaddr, rawsize = struct.unpack_from("<III", image, off+8)
        if vaddr <= rva < vaddr+vsize:
            delta = rva-vaddr
            return {"address": f"0x{va:08x}", "section": name, "section_offset": f"0x{delta:x}", "section_virtual_size": f"0x{vsize:x}", "section_raw_size": f"0x{rawsize:x}", "image_loader_zero_fill": delta >= rawsize}
    raise ValueError(f"0x{va:08x} outside PE sections")

def validate_upstream(relation: Mapping[str, Any], session: Mapping[str, Any]) -> None:
    req(relation.get("format") == RELATION_FORMAT and relation.get("ready") is True, "outer/VHF relation not positive")
    req(relation.get("semantic_authority") == "Process 1", "historical relation authority drift")
    req(obj(relation.get("subject"), "relation subject").get("vehicle") == VEHICLE, "relation vehicle drift")
    req(str(obj(relation.get("subject"), "relation subject").get("canonical_vhf") or "").lower() == CANONICAL_VHF, "relation VHF drift")
    rel = obj(relation.get("relation"), "relation")
    req(rel.get("kind") == "fixed_affine" and rel.get("relation_matrix_numeric_ready") is False, "upstream relation already has a numeric matrix")
    rh = obj(relation.get("handoff"), "relation handoff")
    req(rh.get("outer_vehicle_root_to_VHF_fixed_affine_delta_ready") is True and rh.get("outer_vehicle_root_to_VHF_relation_numeric_matrix_ready") is False, "relation gate drift")
    req(session.get("format") == SESSION_FORMAT and session.get("ready") is True and session.get("vehicle") == VEHICLE and session.get("session_target") == SESSION, "native session drift")
    selector = obj(session.get("selector"), "session selector")
    req(selector.get("source") == "explicit-native-vertical-slice-policy" and selector.get("validated_against_retail_selector_domain") is True, "native session policy drift")

def build_report(relation: Mapping[str, Any], session: Mapping[str, Any], functions: Sequence[Mapping[str, Any]], calls: Sequence[Mapping[str, Any]], source: str, image: bytes, *, native_role: str, first_vehicle_bootstrap: bool) -> dict[str, Any]:
    validate_upstream(relation, session); req(native_role == "primary-player" and first_vehicle_bootstrap, "proof scope requires first primary-player bootstrap")
    req(hashlib.md5(image).hexdigest() == PE_MD5, "retail SHIFT.exe MD5 drift")
    validate_functions(functions); incoming = validate_calls(calls); src = validate_source(source)
    zero = [pe_zero_fill(image, va) for va in ORIGIN_GLOBALS]
    req(all(r["section"] == ".data" and r["image_loader_zero_fill"] for r in zero), "origin globals are not PE .data zero-fill")
    return {
        "format": FORMAT, "version": 1, "status": "bmw-primary-player-first-bootstrap-render-root-delta-proven", "ready": True,
        "vehicle": VEHICLE, "session_target": SESSION, "semantic_authority": "single process",
        "inputs": {"outer_vehicle_vhf_relation": RELATION_FORMAT, "native_session_selector": SESSION_FORMAT, "retail_program": "SHIFT.exe"},
        "native_bootstrap_policy": {"role": "primary-player", "physics_participant_spawn_config_plus_0x10": 0, "first_vehicle_bootstrap": True, "source": "explicit-native-vertical-slice-policy", "retail_live_session_role_observed": False},
        "retail": {"program": "SHIFT.exe", "md5": PE_MD5, "decompiler_source_sha256": SOURCE_SHA256, "incoming_direct_calls": incoming},
        "bootstrap_provenance": {"source_proof": src, "origin_globals_pe_zero_fill": zero, "origin_writer_direct_callers": ["FUN_0074bfd0", "FUN_00794a30", "FUN_0079b2d0"], "selected_prefix": "first primary-player Restart -> role=0 -> InitVehicle -> FUN_00795d60", "origin_writer_reached_before_selected_delta_store": False, "constructor_old_delta": [0.0,0.0,0.0], "image_initial_origin_vector": [0.0,0.0,0.0], "primary_role_formula_evaluation": "old_delta - initial_origin"},
        "selected_numeric": {"delta_local_offsets": ["+0x19c", "+0x1a0", "+0x1a4"], "delta_local": [0.0,0.0,0.0], "producer": "FUN_00795d60", "scope": "first explicit native primary-player vehicle bootstrap before any origin-update path"},
        "handoff": {"BMW_primary_player_first_bootstrap_render_root_delta_numeric_ready": True, "outer_vehicle_root_to_VHF_vehicle_root_ready": True, "outer_vehicle_root_to_VHF_fixed_affine_delta_ready": True, "outer_vehicle_root_to_VHF_relation_numeric_matrix_ready": False, "BODY0_local_to_VHF_vehicle_root_numeric_matrix_ready": False, "BODY0_bind_frame_proof_ready": False, "vehicle_world_transform_ready": False, "consumer": "single-process S2 numeric outer->VHF evaluator, then S3 SHIFT.BMWBody0BindFrameProof/1"},
        "limits": {"first_primary_player_bootstrap_only": True, "delta_zero_claimed_for_restart_or_mode_switch": False, "delta_zero_claimed_for_non_primary_vehicle": False, "native_role_policy_is_retail_live_session_observation": False, "origin_vector_assumed_zero_after_first_origin_update": False, "VHF_root_numeric_matrix_consumed": False, "BODY0_bind_frame_claimed": False, "runtime_capture_used": False, "original_game_executed": False},
        "next_blocker": {"id": "BMW-outer-VHF-numeric-relation-evaluation", "required": "consume exact positive BMW VHF HIERARCHY Root row-vector matrix with delta_local=(0,0,0), then compose selected BMW BODY0->outer"},
    }

def main() -> None:
    p=argparse.ArgumentParser(); p.add_argument("relation",type=Path); p.add_argument("native_session",type=Path); p.add_argument("functions_jsonl",type=Path); p.add_argument("callgraph_jsonl",type=Path); p.add_argument("shift_c",type=Path); p.add_argument("shift_exe",type=Path); p.add_argument("--native-role",required=True,choices=("primary-player",)); p.add_argument("--first-vehicle-bootstrap",action="store_true"); p.add_argument("--json-out",type=Path); a=p.parse_args()
    report=build_report(load_json(a.relation),load_json(a.native_session),load_jsonl(a.functions_jsonl),load_jsonl(a.callgraph_jsonl),a.shift_c.read_text(encoding="utf-8"),a.shift_exe.read_bytes(),native_role=a.native_role,first_vehicle_bootstrap=a.first_vehicle_bootstrap)
    text=json.dumps(report,indent=2,sort_keys=True)+"\n"; a.json_out.write_text(text,encoding="utf-8") if a.json_out else print(text,end="")

if __name__ == "__main__": main()
