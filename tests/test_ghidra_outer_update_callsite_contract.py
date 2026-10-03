import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "tools"
        / "ghidra"
        / "build_outer_update_callsite_contract.py"
    )
    spec = importlib.util.spec_from_file_location(
        "build_outer_update_callsite_contract", path
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write_jsonl(path, rows):
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
    )


def _function(address):
    return {
        "address": address,
        "name": f"FUN_{address[2:]}",
        "size": 64,
        "external": False,
        "thunk": False,
    }


def _call(source, instruction, target):
    return {
        "from_function": source,
        "from_name": f"FUN_{source[2:]}",
        "instruction": instruction,
        "to": target,
        "to_name": f"FUN_{target[2:]}",
        "indirect": False,
    }


def _source_text():
    return r'''void __thiscall FUN_00770e80(void *this,undefined8 param_1,undefined8 param_2,char param_3)
{
  *(undefined8 *)((int)this + 0xa0) = param_2;
  FUN_0076d100(this,param_3);
  FUN_00765470(this,0.5,(double *)0);
  FUN_0076d100(this,param_3);
  *(undefined8 *)((int)this + 0x98) = param_1;
}

void __thiscall
FUN_00794a30(void *this,undefined4 param_1,undefined4 param_2,undefined4 param_3,int param_4,char param_5)
{
  *(ulonglong *)((int)this + 0x1ab0) = CONCAT44(param_4,param_3);
  *(ulonglong *)((int)this + 0x1aa8) = CONCAT44(param_2,param_1);
  if ((param_5 != '\0') && (*(int *)((int)this + 0x234) == 0)) {
    FUN_00770e80(&DAT_00c13700,CONCAT44(param_2,param_1),CONCAT44(param_4,param_3),'\0');
    FUN_0078ef00((int)this);
    FUN_00793ca0(this);
    FUN_007aa750((int)this);
    FUN_007851d0((int)this);
  }
}

undefined4 __fastcall FUN_0079b2d0(void *param_1,undefined4 param_2)
{
  if (*(int *)((int)param_1 + 0x34) != 0) {
    switch(*(undefined4 *)((int)param_1 + 0x234)) {
    case 0:
      FUN_00770e80(&DAT_00c13700,*(undefined8 *)((int)param_1 + 0x1aa8),
                   *(undefined8 *)((int)param_1 + 0x1ab0),'\x01');
      *(undefined8 *)((int)param_1 + 200) = *(undefined8 *)((int)param_1 + 0x1aa8);
      FUN_0078ef00((int)param_1);
      FUN_00793ca0(param_1);
      FUN_007aa750((int)param_1);
      FUN_007851d0((int)param_1);
      break;
    case 1:
      break;
    }
  }
  return 0;
}

void __thiscall FUN_00713050(void *this,int *param_1)
{
  double dVar2;
  double dVar3;
  double dVar4;
  int iVar6;
  int iVar7;
  uint local_14;
  dVar2 = 0.0;
  if (0.0 < *(double *)((int)this + 0x348)) {
    iVar6 = FUN_0070fe90();
    dVar3 = (double)*(int *)(iVar6 + 0x388);
    local_14 = (uint)(longlong)ROUND(dVar3 * *(double *)((int)this + 0x348) + 0.5);
    dVar2 = *(double *)((int)this + 0x160);
    dVar4 = 1.0 / dVar3;
    dVar2 = dVar4 + dVar2;
    (void)*(int *)((int)this + 0x140);
    (void)*(int *)((int)this + 0x144);
    iVar7 = iVar7 + 0x1fa0;
    FUN_00794a30((void *)(*piVar1 + 0x340),(int)*(undefined8 *)((int)this + 0x160),
                 0,0x20000000,0x3fa11111,'\0');
    FUN_00794a30((void *)(*param_1 + 0x340),SUB84(dVar2,0),0,SUB84(dVar4,0),iVar6,'\0');
    FUN_00794a30((void *)(*param_1 + 0x340),SUB84(dVar2,0),0,SUB84(dVar4,0),iVar6,'\x01');
  }
}

undefined4 __thiscall FUN_00715380(void *this,float param_1)
{
  FUN_00713050(this,piVar2);
  return 0;
}
'''


def _fixture(tmp_path):
    module = _load_module()
    source = _source_text()
    source_path = tmp_path / "SHIFT.exe.c"
    source_path.write_text(source, encoding="utf-8")
    source_hash = hashlib.sha256(source.encode("utf-8")).hexdigest()

    (tmp_path / "binary.json").write_text(
        json.dumps(
            {
                "program_name": "SHIFT.exe",
                "executable_md5": module.PE_MD5,
                "language_id": "x86:LE:32:default",
                "image_base": "0x00400000",
                "pointer_size": 4,
            }
        ),
        encoding="utf-8",
    )
    addresses = set(module.SOURCE_FUNCTIONS) | {
        "0x0078ef00",
        "0x00793ca0",
        "0x007aa750",
        "0x007851d0",
        "0x0076d100",
        "0x00765470",
    }
    _write_jsonl(
        tmp_path / "functions.jsonl",
        [_function(address) for address in sorted(addresses)],
    )
    _write_jsonl(
        tmp_path / "callgraph.jsonl",
        [
            _call("0x00794a30", "0x00794a6e", module.OUTER_UPDATE),
            _call("0x0079b2d0", "0x0079b310", module.OUTER_UPDATE),
            _call("0x00713050", "0x00713112", "0x00794a30"),
            _call("0x00713050", "0x00713135", "0x00794a30"),
            _call("0x00713050", "0x007131b5", "0x00794a30"),
            _call("0x00715380", "0x00715434", "0x00713050"),
        ],
    )
    _write_jsonl(
        tmp_path / "switches.jsonl",
        [
            {
                "status": "computed-jump-candidate",
                "function": "0x0079b2d0",
                "name": "FUN_0079b2d0",
                "instruction": "0x0079b2ec",
                "text": "JMP dword ptr [EAX*0x4 + 0x79b46c]",
                "destinations": ["0x0079b2f3", "0x0079b3a7"],
            }
        ],
    )
    return module, source_path, source_hash


def test_builds_source_and_ghidra_callsite_contract(tmp_path):
    module, source_path, source_hash = _fixture(tmp_path)
    report = module.build_outer_update_callsite_contract(
        source_path,
        tmp_path,
        expected_source_sha256=source_hash,
    )

    assert report["format"] == "SHIFT.OuterUpdateCallsiteStatic/1"
    assert report["outer_update"]["receiver_at_callsites"] == "DAT_00c13700"
    assert report["outer_update"]["channel_a_receiver_offset"] == "0x98"
    assert report["outer_update"]["channel_b_receiver_offset"] == "0xa0"
    assert report["outer_update"]["physics_pass_count"] == 2
    assert [row["caller"] for row in report["direct_callsites"]] == [
        "0x00794a30",
        "0x0079b2d0",
    ]
    assert report["direct_callsites"][0]["caller_channel_a_offset"] == "0x1aa8"
    assert report["direct_callsites"][0]["caller_channel_b_offset"] == "0x1ab0"
    assert report["direct_callsites"][0]["outer_mode_argument"] == 0
    assert report["direct_callsites"][1]["outer_mode_argument"] == 1
    assert report["direct_callsites"][1]["direct_incoming_call_count"] == 0
    assert report["upstream_batch_path"]["record_pointer_array_offset"] == "0x140"
    assert report["upstream_batch_path"]["record_count_offset"] == "0x144"
    assert report["upstream_batch_path"]["record_stride"] == "0x1fa0"
    assert report["upstream_batch_path"]["child_object_pointer_adjustment"] == "0x340"
    assert report["upstream_batch_path"]["first_caller_source_call_count"] == 3
    assert report["scope"]["channel_physical_units_proven"] is False
    assert report["scope"]["input_control_ownership_proven"] is False


def test_fails_closed_on_source_hash_mismatch(tmp_path):
    module, source_path, _ = _fixture(tmp_path)
    with pytest.raises(ValueError, match="unexpected SHIFT.exe.c SHA-256"):
        module.build_outer_update_callsite_contract(source_path, tmp_path)


def test_fails_closed_when_source_offset_drifted(tmp_path):
    module, source_path, _ = _fixture(tmp_path)
    source = source_path.read_text(encoding="utf-8").replace(
        "((int)this + 0x1aa8)", "((int)this + 0x1aa0)", 1
    )
    source_path.write_text(source, encoding="utf-8")
    source_hash = hashlib.sha256(source.encode("utf-8")).hexdigest()
    with pytest.raises(ValueError, match="required source fragment missing"):
        module.build_outer_update_callsite_contract(
            source_path,
            tmp_path,
            expected_source_sha256=source_hash,
        )


def test_fails_closed_when_direct_caller_set_changes(tmp_path):
    module, source_path, source_hash = _fixture(tmp_path)
    rows = list(module.read_jsonl(tmp_path / "callgraph.jsonl"))
    rows.append(_call("0x00715380", "0x00715440", module.OUTER_UPDATE))
    _write_jsonl(tmp_path / "callgraph.jsonl", rows)
    with pytest.raises(ValueError, match="direct caller set changed"):
        module.build_outer_update_callsite_contract(
            source_path,
            tmp_path,
            expected_source_sha256=source_hash,
        )


def test_fails_closed_when_second_caller_gains_direct_owner(tmp_path):
    module, source_path, source_hash = _fixture(tmp_path)
    rows = list(module.read_jsonl(tmp_path / "callgraph.jsonl"))
    rows.append(_call("0x00715380", "0x00715450", "0x0079b2d0"))
    _write_jsonl(tmp_path / "callgraph.jsonl", rows)
    with pytest.raises(ValueError, match="expected no direct incoming call"):
        module.build_outer_update_callsite_contract(
            source_path,
            tmp_path,
            expected_source_sha256=source_hash,
        )


def test_fails_closed_when_computed_jump_evidence_changes(tmp_path):
    module, source_path, source_hash = _fixture(tmp_path)
    _write_jsonl(tmp_path / "switches.jsonl", [])
    with pytest.raises(ValueError, match="computed-jump candidate"):
        module.build_outer_update_callsite_contract(
            source_path,
            tmp_path,
            expected_source_sha256=source_hash,
        )
