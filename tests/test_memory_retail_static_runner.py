import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "tools" / "ghidra" / "run_memory_retail_static_evidence.sh"


def _prepare_harness(tmp_path: Path) -> Path:
    tool_dir = tmp_path / "tools" / "ghidra"
    tool_dir.mkdir(parents=True)
    runner = tool_dir / RUNNER.name
    runner.write_text(RUNNER.read_text(encoding="utf-8"), encoding="utf-8")

    forwarding = tool_dir / "run_memory_wrapper_forwarding.sh"
    forwarding.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
printf '%s\\n' \"$@\" > \"${RETAIL_STATIC_FORWARDING_LOG:?}\"
out=$4
mkdir -p -- \"$out\"
printf '%s\\n' '{\"format\":\"SHIFT-MEMORY-WRAPPER-FORWARDING/1\",\"wrapper_count\":5,\"confirmed_wrapper_forwarding_count\":5,\"all_wrapper_forwarding_confirmed\":true}' > \"$out/memory_wrapper_forwarding.json\"
""",
        encoding="utf-8",
    )
    forwarding.chmod(0o755)

    backend = tool_dir / "run_memory_backend_evidence.sh"
    backend.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
printf '%s\\n' \"$@\" > \"${RETAIL_STATIC_BACKEND_LOG:?}\"
out=$5
mkdir -p -- \"$out\"
printf '%s\\n' '{\"format\":\"SHIFT.GhidraFunctionInstructions/1\"}' > \"$out/memory_backend_instructions.jsonl\"
printf '%s\\n' '{\"format\":\"SHIFT-MEMORY-BACKEND-EVIDENCE/1\",\"allocation_backend_diagnostic_proven\":true,\"free_backend_diagnostic_proven\":true,\"release_thunk_to_free_diagnostic_path_proven\":true,\"diagnostic_inventory\":[]}' > \"$out/memory_backend_evidence.json\"
printf '%s\\n' '{\"format\":\"SHIFT-MEMORY-ALLOCATION-DIAGNOSTIC-SLICE/1\",\"allocation_size_role_proven\":true,\"allocation_size_entry_storage\":\"EDX:4\"}' > \"$out/memory_allocation_diagnostic_slice.json\"
printf '%s\\n' '{\"format\":\"SHIFT-MEMORY-FREE-DIAGNOSTIC-SLICE/1\",\"free_pointer_role_proven\":true,\"free_pointer_entry_storage\":\"ECX:4\"}' > \"$out/memory_free_diagnostic_slice.json\"
printf '%s\\n' '{\"format\":\"SHIFT-MEMORY-RELEASE-BYTE-BEHAVIOR/1\",\"analysis_complete\":true,\"thunk_entry_dl_forwarded_to_release_backend\":true,\"release_backend_entry_dl_observed\":true,\"release_backend_entry_dl_controls_conditional_branch\":false,\"release_backend_entry_dl_bitwise_transformed\":false,\"scope\":{\"entry_dl_behavior_observed\":true}}' > \"$out/memory_release_byte_behavior.json\"
""",
        encoding="utf-8",
    )
    backend.chmod(0o755)

    chain = tool_dir / "analyze_release_pointer_chain.py"
    chain.write_text(
        """#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
Path(os.environ['RETAIL_STATIC_CHAIN_LOG']).write_text('\\n'.join(sys.argv[1:]), encoding='utf-8')
out=Path(sys.argv[sys.argv.index('--json-out')+1])
out.write_text(json.dumps({'format':'SHIFT-MEMORY-RELEASE-POINTER-CHAIN/1','release_pointer_to_wrapper_storage_proven':True,'wrapper_paths':[{'wrapper':'FUN_00886930','wrapper_input_storage':'Stack[0x4]:4','released_pointer_path_proven':True}]})+'\\n', encoding='utf-8')
""",
        encoding="utf-8",
    )

    summary = tool_dir / "summarize_memory_retail_static_evidence.py"
    summary.write_text(
        """#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
Path(os.environ['RETAIL_STATIC_SUMMARY_LOG']).write_text('\\n'.join(sys.argv[1:]), encoding='utf-8')
out=Path(sys.argv[sys.argv.index('--json-out')+1])
out.write_text(json.dumps({'format':'SHIFT-MEMORY-RETAIL-STATIC-SUMMARY/1','static_evidence_chain_complete':True})+'\\n', encoding='utf-8')
""",
        encoding="utf-8",
    )
    return runner


def test_runner_builds_source_free_retail_static_evidence(tmp_path):
    runner = _prepare_harness(tmp_path)
    ghidra = tmp_path / "ghidra_export"
    ghidra.mkdir()
    output = tmp_path / "out"
    forwarding_log = tmp_path / "forwarding.log"
    backend_log = tmp_path / "backend.log"
    chain_log = tmp_path / "chain.log"
    summary_log = tmp_path / "summary.log"
    env = dict(os.environ)
    env["GHIDRA_HOME"] = "/opt/fake-ghidra"
    env["RETAIL_STATIC_FORWARDING_LOG"] = str(forwarding_log)
    env["RETAIL_STATIC_BACKEND_LOG"] = str(backend_log)
    env["RETAIL_STATIC_CHAIN_LOG"] = str(chain_log)
    env["RETAIL_STATIC_SUMMARY_LOG"] = str(summary_log)

    result = subprocess.run(
        [
            "bash", str(runner), "/projects/shift", "shift", "SHIFT.exe",
            str(ghidra), str(output),
        ],
        env=env, text=True, capture_output=True, check=True,
    )

    out = output.resolve()
    export = ghidra.resolve()
    assert forwarding_log.read_text(encoding="utf-8").splitlines() == [
        "/projects/shift", "shift", "SHIFT.exe", str(out / "forwarding"),
    ]
    assert backend_log.read_text(encoding="utf-8").splitlines() == [
        "/projects/shift", "shift", "SHIFT.exe", str(export), str(out / "backend"),
    ]
    assert chain_log.read_text(encoding="utf-8").splitlines() == [
        str(out / "backend" / "memory_backend_instructions.jsonl"),
        "--free-slice", str(out / "backend" / "memory_free_diagnostic_slice.json"),
        "--forwarding", str(out / "forwarding" / "memory_wrapper_forwarding.json"),
        "--json-out", str(out / "memory_release_pointer_chain.json"),
    ]
    assert summary_log.read_text(encoding="utf-8").splitlines() == [
        "--forwarding", str(out / "forwarding" / "memory_wrapper_forwarding.json"),
        "--backend", str(out / "backend" / "memory_backend_evidence.json"),
        "--allocation-slice", str(out / "backend" / "memory_allocation_diagnostic_slice.json"),
        "--free-slice", str(out / "backend" / "memory_free_diagnostic_slice.json"),
        "--release-chain", str(out / "memory_release_pointer_chain.json"),
        "--release-byte", str(out / "backend" / "memory_release_byte_behavior.json"),
        "--json-out", str(out / "memory_retail_static_summary.json"),
    ]
    summary = json.loads((output / "memory_retail_static_summary.json").read_text())
    assert summary["format"] == "SHIFT-MEMORY-RETAIL-STATIC-SUMMARY/1"
    assert "retail static summary:" in result.stdout


def test_runner_rejects_missing_ghidra_export(tmp_path):
    runner = _prepare_harness(tmp_path)
    env = dict(os.environ)
    env["GHIDRA_HOME"] = "/opt/fake-ghidra"
    result = subprocess.run(
        ["bash", str(runner), "/projects/shift", "shift", "SHIFT.exe", str(tmp_path / "missing"), str(tmp_path / "out")],
        env=env, text=True, capture_output=True,
    )
    assert result.returncode == 1
    assert "Ghidra export directory not found" in result.stderr


def test_runner_rejects_wrong_argument_count(tmp_path):
    runner = _prepare_harness(tmp_path)
    env = dict(os.environ)
    env["GHIDRA_HOME"] = "/opt/fake-ghidra"
    result = subprocess.run(["bash", str(runner), "a", "b"], env=env, text=True, capture_output=True)
    assert result.returncode == 2
    assert "Usage:" in result.stderr
