import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "tools" / "ghidra" / "run_memory_wrapper_full_evidence.sh"


def _prepare_harness(tmp_path: Path) -> Path:
    ghidra_dir = tmp_path / "tools" / "ghidra"
    live_dir = tmp_path / "tools" / "shift_live_dump"
    ghidra_dir.mkdir(parents=True)
    live_dir.mkdir(parents=True)

    runner = ghidra_dir / RUNNER.name
    runner.write_text(RUNNER.read_text(encoding="utf-8"), encoding="utf-8")

    forwarding = ghidra_dir / "run_memory_wrapper_forwarding.sh"
    forwarding.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
printf '%s\\n' \"$@\" > \"${FULL_WRAPPER_FORWARDING_LOG:?}\"
out=$4
mkdir -p -- \"$out\"
printf '%s\\n' '{\"format\":\"SHIFT-MEMORY-WRAPPER-FORWARDING/1\",\"wrappers\":[]}' > \"$out/memory_wrapper_forwarding.json\"
""",
        encoding="utf-8",
    )
    forwarding.chmod(0o755)

    backend = ghidra_dir / "run_memory_backend_evidence.sh"
    backend.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
printf '%s\\n' \"$@\" > \"${FULL_WRAPPER_BACKEND_LOG:?}\"
out=$5
mkdir -p -- \"$out\"
printf '%s\\n' '{\"format\":\"SHIFT.GhidraFunctionInstructions/1\"}' > \"$out/memory_backend_instructions.jsonl\"
printf '%s\\n' '{\"format\":\"SHIFT-MEMORY-BACKEND-EVIDENCE/1\"}' > \"$out/memory_backend_evidence.json\"
printf '%s\\n' '{\"format\":\"SHIFT-MEMORY-ALLOCATION-DIAGNOSTIC-SLICE/1\",\"allocation_size_role_proven\":false,\"allocation_size_entry_storage\":null}' > \"$out/memory_allocation_diagnostic_slice.json\"
printf '%s\\n' '{\"format\":\"SHIFT-MEMORY-FREE-DIAGNOSTIC-SLICE/1\",\"free_pointer_role_proven\":false,\"free_pointer_entry_storage\":null}' > \"$out/memory_free_diagnostic_slice.json\"
""",
        encoding="utf-8",
    )
    backend.chmod(0o755)

    release_chain = ghidra_dir / "analyze_release_pointer_chain.py"
    release_chain.write_text(
        """#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path
Path(os.environ['FULL_WRAPPER_RELEASE_CHAIN_LOG']).write_text('\\n'.join(sys.argv[1:]), encoding='utf-8')
assert Path(sys.argv[1]).is_file()
assert sys.argv[2] == '--free-slice'
assert Path(sys.argv[3]).is_file()
assert sys.argv[4] == '--forwarding'
assert Path(sys.argv[5]).is_file()
assert sys.argv[6] == '--json-out'
out = Path(sys.argv[7])
out.write_text(json.dumps({'format':'SHIFT-MEMORY-RELEASE-POINTER-CHAIN/1','release_pointer_to_wrapper_storage_proven':False,'wrapper_paths':[]}) + '\\n', encoding='utf-8')
""",
        encoding="utf-8",
    )

    extractor = live_dir / "extract_memory_wrapper_callsites.py"
    extractor.write_text(
        """#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path
Path(os.environ['FULL_WRAPPER_CALLSITE_LOG']).write_text('\\n'.join(sys.argv[1:]), encoding='utf-8')
out = Path(sys.argv[sys.argv.index('--json-out') + 1])
out.write_text(json.dumps({'format':'SHIFT-MEMORY-WRAPPER-CALLSITE-EVIDENCE/1','callsites':[]}) + '\\n', encoding='utf-8')
""",
        encoding="utf-8",
    )

    joiner = live_dir / "join_memory_wrapper_argument_evidence.py"
    joiner.write_text(
        """#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path
Path(os.environ['FULL_WRAPPER_JOIN_LOG']).write_text('\\n'.join(sys.argv[1:]), encoding='utf-8')
out = Path(sys.argv[sys.argv.index('--json-out') + 1])
out.write_text(json.dumps({'format':'SHIFT-MEMORY-WRAPPER-ARGUMENT-JOIN/1','rows':[]}) + '\\n', encoding='utf-8')
""",
        encoding="utf-8",
    )

    summarizer = live_dir / "summarize_memory_wrapper_argument_patterns.py"
    summarizer.write_text(
        """#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path
Path(os.environ['FULL_WRAPPER_PATTERN_LOG']).write_text('\\n'.join(sys.argv[1:]), encoding='utf-8')
out = Path(sys.argv[sys.argv.index('--json-out') + 1])
out.write_text(json.dumps({'format':'SHIFT-MEMORY-WRAPPER-PROVENANCE-PATTERNS/1'}) + '\\n', encoding='utf-8')
""",
        encoding="utf-8",
    )

    role_joiner = live_dir / "join_allocation_size_role.py"
    role_joiner.write_text(
        """#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path
Path(os.environ['FULL_WRAPPER_ROLE_JOIN_LOG']).write_text('\\n'.join(sys.argv[1:]), encoding='utf-8')
assert Path(sys.argv[1]).is_file()
assert sys.argv[2] == '--diagnostic-slice'
assert Path(sys.argv[3]).is_file()
assert sys.argv[4] == '--json-out'
out = Path(sys.argv[5])
out.write_text(json.dumps({'format':'SHIFT-MEMORY-ALLOCATION-SIZE-ROLE-JOIN/1','rows':[]}) + '\\n', encoding='utf-8')
""",
        encoding="utf-8",
    )

    released_pointer_joiner = live_dir / "join_released_pointer_role.py"
    released_pointer_joiner.write_text(
        """#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path
Path(os.environ['FULL_WRAPPER_RELEASED_POINTER_JOIN_LOG']).write_text('\\n'.join(sys.argv[1:]), encoding='utf-8')
assert Path(sys.argv[1]).is_file()
assert sys.argv[2] == '--release-chain'
assert Path(sys.argv[3]).is_file()
assert sys.argv[4] == '--json-out'
out = Path(sys.argv[5])
out.write_text(json.dumps({'format':'SHIFT-MEMORY-RELEASED-POINTER-ROLE-JOIN/1','rows':[]}) + '\\n', encoding='utf-8')
""",
        encoding="utf-8",
    )
    return runner


def test_runner_builds_wrapper_backend_and_semantic_evidence(tmp_path):
    runner = _prepare_harness(tmp_path)
    source = tmp_path / "SHIFT.exe.c"
    source.write_text("/* recovered source */\n", encoding="utf-8")
    ghidra_export = tmp_path / "ghidra_export"
    ghidra_export.mkdir()
    output = tmp_path / "out"
    callsite_log = tmp_path / "callsites.log"
    forwarding_log = tmp_path / "forwarding.log"
    join_log = tmp_path / "join.log"
    pattern_log = tmp_path / "patterns.log"
    backend_log = tmp_path / "backend.log"
    role_join_log = tmp_path / "role_join.log"
    release_chain_log = tmp_path / "release_chain.log"
    released_pointer_join_log = tmp_path / "released_pointer_join.log"

    env = dict(os.environ)
    env["GHIDRA_HOME"] = "/opt/fake-ghidra"
    env["FULL_WRAPPER_CALLSITE_LOG"] = str(callsite_log)
    env["FULL_WRAPPER_FORWARDING_LOG"] = str(forwarding_log)
    env["FULL_WRAPPER_JOIN_LOG"] = str(join_log)
    env["FULL_WRAPPER_PATTERN_LOG"] = str(pattern_log)
    env["FULL_WRAPPER_BACKEND_LOG"] = str(backend_log)
    env["FULL_WRAPPER_ROLE_JOIN_LOG"] = str(role_join_log)
    env["FULL_WRAPPER_RELEASE_CHAIN_LOG"] = str(release_chain_log)
    env["FULL_WRAPPER_RELEASED_POINTER_JOIN_LOG"] = str(released_pointer_join_log)

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

    resolved_output = output.resolve()
    resolved_source = source.resolve()
    resolved_export = ghidra_export.resolve()

    assert callsite_log.read_text(encoding="utf-8").splitlines() == [
        str(resolved_source),
        "--ghidra-export",
        str(resolved_export),
        "--json-out",
        str(resolved_output / "memory_wrapper_callsites.json"),
    ]
    assert forwarding_log.read_text(encoding="utf-8").splitlines() == [
        "/projects/shift",
        "shift",
        "SHIFT.exe",
        str(resolved_output / "forwarding"),
    ]
    assert join_log.read_text(encoding="utf-8").splitlines() == [
        str(resolved_output / "memory_wrapper_callsites.json"),
        "--forwarding",
        str(resolved_output / "forwarding" / "memory_wrapper_forwarding.json"),
        "--json-out",
        str(resolved_output / "memory_wrapper_argument_join.json"),
    ]
    assert pattern_log.read_text(encoding="utf-8").splitlines() == [
        str(resolved_output / "memory_wrapper_argument_join.json"),
        "--json-out",
        str(resolved_output / "memory_wrapper_provenance_patterns.json"),
    ]
    assert backend_log.read_text(encoding="utf-8").splitlines() == [
        "/projects/shift",
        "shift",
        "SHIFT.exe",
        str(resolved_export),
        str(resolved_output / "backend"),
    ]
    assert role_join_log.read_text(encoding="utf-8").splitlines() == [
        str(resolved_output / "memory_wrapper_argument_join.json"),
        "--diagnostic-slice",
        str(resolved_output / "backend" / "memory_allocation_diagnostic_slice.json"),
        "--json-out",
        str(resolved_output / "memory_allocation_size_role_join.json"),
    ]
    assert release_chain_log.read_text(encoding="utf-8").splitlines() == [
        str(resolved_output / "backend" / "memory_backend_instructions.jsonl"),
        "--free-slice",
        str(resolved_output / "backend" / "memory_free_diagnostic_slice.json"),
        "--forwarding",
        str(resolved_output / "forwarding" / "memory_wrapper_forwarding.json"),
        "--json-out",
        str(resolved_output / "memory_release_pointer_chain.json"),
    ]
    assert released_pointer_join_log.read_text(encoding="utf-8").splitlines() == [
        str(resolved_output / "memory_wrapper_argument_join.json"),
        "--release-chain",
        str(resolved_output / "memory_release_pointer_chain.json"),
        "--json-out",
        str(resolved_output / "memory_released_pointer_role_join.json"),
    ]

    joined = json.loads((output / "memory_wrapper_argument_join.json").read_text(encoding="utf-8"))
    assert joined["format"] == "SHIFT-MEMORY-WRAPPER-ARGUMENT-JOIN/1"
    patterns = json.loads((output / "memory_wrapper_provenance_patterns.json").read_text(encoding="utf-8"))
    assert patterns["format"] == "SHIFT-MEMORY-WRAPPER-PROVENANCE-PATTERNS/1"
    backend_report = json.loads((output / "backend" / "memory_backend_evidence.json").read_text(encoding="utf-8"))
    assert backend_report["format"] == "SHIFT-MEMORY-BACKEND-EVIDENCE/1"
    role_report = json.loads((output / "memory_allocation_size_role_join.json").read_text(encoding="utf-8"))
    assert role_report["format"] == "SHIFT-MEMORY-ALLOCATION-SIZE-ROLE-JOIN/1"
    release_report = json.loads((output / "memory_release_pointer_chain.json").read_text(encoding="utf-8"))
    assert release_report["format"] == "SHIFT-MEMORY-RELEASE-POINTER-CHAIN/1"
    released_pointer_report = json.loads((output / "memory_released_pointer_role_join.json").read_text(encoding="utf-8"))
    assert released_pointer_report["format"] == "SHIFT-MEMORY-RELEASED-POINTER-ROLE-JOIN/1"
    assert "memory wrapper callsites:" in result.stdout
    assert "memory wrapper forwarding:" in result.stdout
    assert "memory wrapper argument join:" in result.stdout
    assert "memory wrapper provenance patterns:" in result.stdout
    assert "memory backend evidence:" in result.stdout
    assert "memory allocation-size role join:" in result.stdout
    assert "memory release-pointer chain:" in result.stdout
    assert "memory released-pointer role join:" in result.stdout


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
