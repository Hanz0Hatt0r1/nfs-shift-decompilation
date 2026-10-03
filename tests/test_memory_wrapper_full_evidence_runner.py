import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "tools" / "ghidra" / "run_memory_wrapper_full_evidence.sh"


def _write_script(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")
    path.chmod(0o755)


def _prepare_harness(tmp_path: Path) -> Path:
    ghidra_dir = tmp_path / "tools" / "ghidra"
    live_dir = tmp_path / "tools" / "shift_live_dump"
    ghidra_dir.mkdir(parents=True)
    live_dir.mkdir(parents=True)

    runner = ghidra_dir / RUNNER.name
    runner.write_text(RUNNER.read_text(encoding="utf-8"), encoding="utf-8")

    _write_script(
        ghidra_dir / "run_memory_wrapper_forwarding.sh",
        r"""#!/usr/bin/env bash
set -euo pipefail
out=$4
mkdir -p -- "$out"
printf '%s\n' '{"format":"SHIFT-MEMORY-WRAPPER-FORWARDING/1","wrapper_count":0,"confirmed_wrapper_forwarding_count":0,"all_wrapper_forwarding_confirmed":false,"wrappers":[]}' > "$out/memory_wrapper_forwarding.json"
""",
    )
    _write_script(
        ghidra_dir / "run_memory_backend_evidence.sh",
        r"""#!/usr/bin/env bash
set -euo pipefail
out=$5
mkdir -p -- "$out"
printf '%s\n' '{"format":"SHIFT.GhidraFunctionInstructions/1"}' > "$out/memory_backend_instructions.jsonl"
printf '%s\n' '{"format":"SHIFT-MEMORY-BACKEND-EVIDENCE/1"}' > "$out/memory_backend_evidence.json"
printf '%s\n' '{"format":"SHIFT-MEMORY-ALLOCATION-DIAGNOSTIC-SLICE/1","allocation_size_role_proven":false,"allocation_size_entry_storage":null}' > "$out/memory_allocation_diagnostic_slice.json"
printf '%s\n' '{"format":"SHIFT-MEMORY-FREE-DIAGNOSTIC-SLICE/1","free_pointer_role_proven":false,"free_pointer_entry_storage":null}' > "$out/memory_free_diagnostic_slice.json"
printf '%s\n' '{"format":"SHIFT-MEMORY-RELEASE-BYTE-BEHAVIOR/1","analysis_complete":true,"scope":{"entry_dl_behavior_observed":true,"release_flag_role_proven":false}}' > "$out/memory_release_byte_behavior.json"
""",
    )
    _write_script(
        ghidra_dir / "analyze_release_pointer_chain.py",
        r"""#!/usr/bin/env python3
import json, sys
from pathlib import Path
out = Path(sys.argv[sys.argv.index('--json-out') + 1])
out.write_text(json.dumps({'format':'SHIFT-MEMORY-RELEASE-POINTER-CHAIN/1','release_pointer_to_wrapper_storage_proven':False,'wrapper_paths':[]}) + '\n', encoding='utf-8')
""",
    )
    _write_script(
        ghidra_dir / "summarize_memory_retail_static_evidence.py",
        r"""#!/usr/bin/env python3
import json, sys
from pathlib import Path
out = Path(sys.argv[sys.argv.index('--json-out') + 1])
out.write_text(json.dumps({'format':'SHIFT-MEMORY-RETAIL-STATIC-SUMMARY/1','static_evidence_chain_complete':False,'release_byte_behavior':{'analysis_complete':True},'scope':{'release_byte_behavior_observed':True,'release_flag_role_proven':False}}) + '\n', encoding='utf-8')
""",
    )

    _write_script(
        live_dir / "extract_memory_wrapper_callsites.py",
        r"""#!/usr/bin/env python3
import json, sys
from pathlib import Path
out = Path(sys.argv[sys.argv.index('--json-out') + 1])
out.write_text(json.dumps({'format':'SHIFT-MEMORY-WRAPPER-CALLSITE-EVIDENCE/1','callsites':[]}) + '\n', encoding='utf-8')
""",
    )
    _write_script(
        live_dir / "join_memory_wrapper_argument_evidence.py",
        r"""#!/usr/bin/env python3
import json, sys
from pathlib import Path
out = Path(sys.argv[sys.argv.index('--json-out') + 1])
out.write_text(json.dumps({'format':'SHIFT-MEMORY-WRAPPER-ARGUMENT-JOIN/1','rows':[]}) + '\n', encoding='utf-8')
""",
    )
    _write_script(
        live_dir / "summarize_memory_wrapper_argument_patterns.py",
        r"""#!/usr/bin/env python3
import json, sys
from pathlib import Path
out = Path(sys.argv[sys.argv.index('--json-out') + 1])
out.write_text(json.dumps({'format':'SHIFT-MEMORY-WRAPPER-PROVENANCE-PATTERNS/1'}) + '\n', encoding='utf-8')
""",
    )
    _write_script(
        live_dir / "join_allocation_size_role.py",
        r"""#!/usr/bin/env python3
import json, sys
from pathlib import Path
out = Path(sys.argv[sys.argv.index('--json-out') + 1])
out.write_text(json.dumps({'format':'SHIFT-MEMORY-ALLOCATION-SIZE-ROLE-JOIN/1','rows':[],'scope':{'allocation_size_role_proven':False}}) + '\n', encoding='utf-8')
""",
    )
    _write_script(
        live_dir / "join_released_pointer_role.py",
        r"""#!/usr/bin/env python3
import json, sys
from pathlib import Path
out = Path(sys.argv[sys.argv.index('--json-out') + 1])
out.write_text(json.dumps({'format':'SHIFT-MEMORY-RELEASED-POINTER-ROLE-JOIN/1','rows':[],'scope':{'released_pointer_role_proven':False}}) + '\n', encoding='utf-8')
""",
    )
    _write_script(
        live_dir / "summarize_memory_source_semantics.py",
        r"""#!/usr/bin/env python3
import json, sys
from pathlib import Path
out = Path(sys.argv[sys.argv.index('--json-out') + 1])
out.write_text(json.dumps({'format':'SHIFT-MEMORY-SOURCE-SEMANTIC-SUMMARY/1','wrapper_profiles':[],'scope':{'release_flag_role_proven':False}}) + '\n', encoding='utf-8')
""",
    )
    return runner


def test_runner_builds_complete_memory_evidence_bundle(tmp_path):
    runner = _prepare_harness(tmp_path)
    source = tmp_path / "SHIFT.exe.c"
    source.write_text("/* recovered source */\n", encoding="utf-8")
    ghidra_export = tmp_path / "ghidra_export"
    ghidra_export.mkdir()
    output = tmp_path / "out"

    env = dict(os.environ)
    env["GHIDRA_HOME"] = "/opt/fake-ghidra"
    result = subprocess.run(
        [
            "bash",
            str(runner),
            str(source),
            str(ghidra_export),
            "/projects/shift",
            "shift",
            "SHIFT.exe",
            str(output),
        ],
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    expected = {
        "memory_wrapper_callsites.json": "SHIFT-MEMORY-WRAPPER-CALLSITE-EVIDENCE/1",
        "memory_wrapper_argument_join.json": "SHIFT-MEMORY-WRAPPER-ARGUMENT-JOIN/1",
        "memory_wrapper_provenance_patterns.json": "SHIFT-MEMORY-WRAPPER-PROVENANCE-PATTERNS/1",
        "memory_allocation_size_role_join.json": "SHIFT-MEMORY-ALLOCATION-SIZE-ROLE-JOIN/1",
        "memory_release_pointer_chain.json": "SHIFT-MEMORY-RELEASE-POINTER-CHAIN/1",
        "memory_released_pointer_role_join.json": "SHIFT-MEMORY-RELEASED-POINTER-ROLE-JOIN/1",
        "memory_retail_static_summary.json": "SHIFT-MEMORY-RETAIL-STATIC-SUMMARY/1",
        "memory_source_semantic_summary.json": "SHIFT-MEMORY-SOURCE-SEMANTIC-SUMMARY/1",
    }
    for relative, expected_format in expected.items():
        report = json.loads((output / relative).read_text(encoding="utf-8"))
        assert report["format"] == expected_format

    backend_expected = {
        "memory_backend_evidence.json": "SHIFT-MEMORY-BACKEND-EVIDENCE/1",
        "memory_allocation_diagnostic_slice.json": "SHIFT-MEMORY-ALLOCATION-DIAGNOSTIC-SLICE/1",
        "memory_free_diagnostic_slice.json": "SHIFT-MEMORY-FREE-DIAGNOSTIC-SLICE/1",
        "memory_release_byte_behavior.json": "SHIFT-MEMORY-RELEASE-BYTE-BEHAVIOR/1",
    }
    for relative, expected_format in backend_expected.items():
        report = json.loads((output / "backend" / relative).read_text(encoding="utf-8"))
        assert report["format"] == expected_format

    assert "memory retail static summary:" in result.stdout
    assert "memory source semantic summary:" in result.stdout


def test_runner_rejects_missing_inputs_before_subtools(tmp_path):
    runner = _prepare_harness(tmp_path)
    env = dict(os.environ)
    env["GHIDRA_HOME"] = "/opt/fake-ghidra"
    result = subprocess.run(
        [
            "bash",
            str(runner),
            str(tmp_path / "missing.c"),
            str(tmp_path / "missing-ghidra"),
            "/projects/shift",
            "shift",
            "SHIFT.exe",
            str(tmp_path / "out"),
        ],
        env=env,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 1
    assert "recovered source not found" in result.stderr


def test_runner_rejects_wrong_argument_count(tmp_path):
    runner = _prepare_harness(tmp_path)
    env = dict(os.environ)
    env["GHIDRA_HOME"] = "/opt/fake-ghidra"
    result = subprocess.run(
        ["bash", str(runner), "a", "b"],
        env=env,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 2
    assert "Usage:" in result.stderr
