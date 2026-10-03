import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "tools" / "ghidra" / "run_body_writer_bridge_pipeline.sh"


def _script(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")
    path.chmod(0o755)


def _prepare(tmp_path: Path) -> Path:
    tools = tmp_path / "tools" / "ghidra"
    tools.mkdir(parents=True)
    runner = tools / RUNNER.name
    runner.write_text(RUNNER.read_text(encoding="utf-8"), encoding="utf-8")

    _script(
        tools / "build_proven_callgraph_frontier.py",
        r'''#!/usr/bin/env python3
import json, sys
from pathlib import Path
args=sys.argv[1:]
out=Path(args[args.index('--json-out')+1]); targets=Path(args[args.index('--targets-out')+1])
assert args[args.index('--max-depth')+1] == '3'
assert args[args.index('--max-targets')+1] == '7'
out.write_text(json.dumps({'format':'SHIFT.GhidraProvenCallgraphFrontier/1','instruction_export_target_count':2})+'\n',encoding='utf-8')
targets.write_text('0x0076d100\n0x00700000\n',encoding='utf-8')
''',
    )
    _script(
        tools / "run_shift_function_instructions.sh",
        r'''#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$@" > "${BODY_PIPELINE_EXPORT_LOG:?}"
out=$4
printf '%s\n' '{"format":"SHIFT.GhidraFunctionInstructions/2","found":true,"function":{"address":"0x0076d100"},"instructions":[{"address":"0x0076d101","mnemonic":"MOV","operands":["EAX","dword ptr [ECX + 0x48]"],"pcode":[{"opcode":"LOAD","text":"x = LOAD y"}]}]}' > "$out"
''',
    )
    _script(
        tools / "analyze_register_relative_accesses.py",
        r'''#!/usr/bin/env python3
import json, sys
from pathlib import Path
source=Path(sys.argv[1]); assert json.loads(source.read_text())['format']=='SHIFT.GhidraFunctionInstructions/2'
out=Path(sys.argv[sys.argv.index('--json-out')+1])
out.write_text(json.dumps({'format':'SHIFT.GhidraRegisterRelativeAccesses/1','access_count':4,'accesses':[]})+'\n',encoding='utf-8')
''',
    )
    _script(
        tools / "build_body_writer_bridge_candidates.py",
        r'''#!/usr/bin/env python3
import json, sys
from pathlib import Path
out=Path(sys.argv[sys.argv.index('--json-out')+1])
out.write_text(json.dumps({'format':'SHIFT.BodyWriterBridgeCandidates/1','candidate_count':2,'combined_bridge_group_count':1,'candidates':[]})+'\n',encoding='utf-8')
''',
    )
    _script(
        tools / "join_body_writer_candidates_to_frontier.py",
        r'''#!/usr/bin/env python3
import json, sys
from pathlib import Path
out=Path(sys.argv[sys.argv.index('--json-out')+1])
out.write_text(json.dumps({'format':'SHIFT.BodyWriterBridgeFrontierJoin/1','proven_slice_root_candidate_count':0,'frontier_candidate_count':2,'outside_frontier_candidate_count':0})+'\n',encoding='utf-8')
''',
    )
    return runner


def test_runner_builds_complete_body_writer_bridge_bundle(tmp_path):
    runner = _prepare(tmp_path)
    ghidra_export = tmp_path / "ghidra"
    ghidra_export.mkdir()
    output = tmp_path / "out"
    log = tmp_path / "export-args.txt"
    env = dict(os.environ)
    env["GHIDRA_HOME"] = "/opt/fake-ghidra"
    env["SHIFT_BODY_FRONTIER_MAX_DEPTH"] = "3"
    env["SHIFT_BODY_FRONTIER_MAX_TARGETS"] = "7"
    env["BODY_PIPELINE_EXPORT_LOG"] = str(log)

    result = subprocess.run(
        [
            "bash", str(runner), str(ghidra_export), "/projects/shift",
            "shift", "SHIFT.exe", str(output),
        ],
        env=env, text=True, capture_output=True, check=True,
    )

    args = log.read_text(encoding="utf-8").splitlines()
    assert args[:4] == [
        "/projects/shift", "shift", "SHIFT.exe",
        str(output.resolve() / "physics_vehicle_frontier_instructions.jsonl"),
    ]
    assert args[4:] == ["0x0076d100", "0x00700000"]

    manifest = json.loads(
        (output / "body_writer_bridge_pipeline_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["format"] == "SHIFT.BodyWriterBridgePipelineManifest/1"
    assert manifest["instruction_export_target_count"] == 2
    assert manifest["register_relative_access_count"] == 4
    assert manifest["bridge_candidate_count"] == 2
    assert manifest["combined_bridge_group_count"] == 1
    assert manifest["frontier_candidate_count"] == 2
    assert manifest["outside_frontier_candidate_count"] == 0
    assert manifest["scope"]["body_pointer_provenance_resolved"] is False
    assert "BODY writer pipeline manifest:" in result.stdout


def test_runner_rejects_missing_ghidra_export(tmp_path):
    runner = _prepare(tmp_path)
    env = dict(os.environ)
    env["GHIDRA_HOME"] = "/opt/fake-ghidra"
    result = subprocess.run(
        [
            "bash", str(runner), str(tmp_path / "missing"), "/projects/shift",
            "shift", "SHIFT.exe", str(tmp_path / "out"),
        ],
        env=env, text=True, capture_output=True,
    )
    assert result.returncode == 1
    assert "Ghidra export directory not found" in result.stderr


def test_runner_rejects_invalid_frontier_limits(tmp_path):
    runner = _prepare(tmp_path)
    ghidra_export = tmp_path / "ghidra"
    ghidra_export.mkdir()
    env = dict(os.environ)
    env["GHIDRA_HOME"] = "/opt/fake-ghidra"
    env["SHIFT_BODY_FRONTIER_MAX_DEPTH"] = "zero"
    result = subprocess.run(
        [
            "bash", str(runner), str(ghidra_export), "/projects/shift",
            "shift", "SHIFT.exe", str(tmp_path / "out"),
        ],
        env=env, text=True, capture_output=True,
    )
    assert result.returncode == 2
    assert "SHIFT_BODY_FRONTIER_MAX_DEPTH must be a positive integer" in result.stderr
