from __future__ import annotations

import json
import os
import stat
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "tools" / "ghidra" / "run_p1b_manager374_helper_setter_ghidra_headless.sh"


def make_fake_ghidra(tmp_path: Path, *, exit_code: int = 0) -> Path:
    ghidra_home = tmp_path / "ghidra"
    support = ghidra_home / "support"
    support.mkdir(parents=True)
    fake = support / "analyzeHeadless"
    fake.write_text(
        f'''#!/usr/bin/env python3
import gzip
import json
import os
import sys
from pathlib import Path

args = sys.argv[1:]
assert "-readOnly" in args
assert "-noanalysis" in args
script_i = args.index("-scriptPath")
script_dir = Path(args[script_i + 1])
assert sorted(p.name for p in script_dir.iterdir()) == ["ShiftCompactInstructionStreamExporter.java"]
post_i = args.index("-postScript")
assert args[post_i + 1] == "ShiftCompactInstructionStreamExporter.java"
out = Path(args[post_i + 2])
print("FAKE_GHIDRA_HEADLESS_OK")
if {exit_code} != 0:
    raise SystemExit({exit_code})
header = {{
    "format": "SHIFT.GhidraCompactInstructionStream/1",
    "kind": "header",
    "program": "SHIFT.exe",
    "executable_md5": "705af8b420e5eb1e3834ac43d5533c6b",
    "language_id": "x86:LE:32:default",
    "image_base": "0x00400000",
    "pointer_size": 4,
}}
row = {{
    "format": "SHIFT.GhidraCompactInstructionStream/1",
    "kind": "instruction",
    "address": "0x00401000",
    "mnemonic": "RET",
    "operands": [],
    "flow_type": "TERMINATOR",
    "flows": [],
}}
with gzip.open(out, "wt", encoding="utf-8") as stream:
    stream.write(json.dumps(header) + "\\n")
    stream.write(json.dumps(row) + "\\n")
''',
        encoding="utf-8",
    )
    fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
    return ghidra_home


def run_wrapper(tmp_path: Path, ghidra_home: Path, out_dir: Path, *, extra_env: dict[str, str] | None = None):
    project_dir = tmp_path / "project"
    project_dir.mkdir(exist_ok=True)
    env = os.environ.copy()
    env["GHIDRA_HOME"] = str(ghidra_home)
    env["SHIFT_GHIDRA_HEADLESS_TIMEOUT_SECONDS"] = "30"
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [
            "bash",
            str(RUNNER),
            str(project_dir),
            "shift",
            "SHIFT.exe",
            str(out_dir),
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_headless_wrapper_exports_analyzes_and_publishes_atomically(tmp_path: Path) -> None:
    ghidra_home = make_fake_ghidra(tmp_path)
    out_dir = tmp_path / "evidence" / "helper-setter-ghidra"

    result = run_wrapper(tmp_path, ghidra_home, out_dir)
    assert result.returncode == 0, result.stderr
    assert "P1B Ghidra helper-setter acquisition ready" in result.stdout

    expected = {
        "ghidra_acquisition.json",
        "frontier.json",
        "direct_call_argument.json",
        "helper_return_immediate.json",
        "helper_return_stack.json",
        "compact_instruction_stream.jsonl.gz",
        "ghidra_headless.log",
    }
    assert {path.name for path in out_dir.iterdir()} == expected
    assert "FAKE_GHIDRA_HEADLESS_OK" in (out_dir / "ghidra_headless.log").read_text(encoding="utf-8")

    acquisition = json.loads((out_dir / "ghidra_acquisition.json").read_text(encoding="utf-8"))
    assert acquisition["format"] == "SHIFT.P1B.Manager374GhidraHelperSetterAcquisition/1"
    assert acquisition["source_stream"]["instruction_count"] == 1
    assert acquisition["source_stream"]["path_name"] == "compact_instruction_stream.jsonl.gz"
    assert acquisition["authority"]["raw_executable_sha256_verified_in_this_run"] is False
    assert acquisition["adjudication"]["global_helper_non_vtable_indirect_setter_surface_complete"] is False
    assert acquisition["adjudication"]["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert acquisition["adjudication"]["external_provider_count"] == 7

    assert list((tmp_path / "evidence").glob(".p1b-helper-setter-ghidra.*")) == []


def test_headless_wrapper_refuses_nonempty_destination_without_running_ghidra(tmp_path: Path) -> None:
    ghidra_home = make_fake_ghidra(tmp_path)
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    sentinel = out_dir / "keep.txt"
    sentinel.write_text("do not overwrite", encoding="utf-8")

    result = run_wrapper(tmp_path, ghidra_home, out_dir)
    assert result.returncode == 2
    assert "output directory must be empty" in result.stderr
    assert sentinel.read_text(encoding="utf-8") == "do not overwrite"
    assert "FAKE_GHIDRA_HEADLESS_OK" not in result.stdout


def test_headless_failure_never_publishes_partial_evidence(tmp_path: Path) -> None:
    ghidra_home = make_fake_ghidra(tmp_path, exit_code=9)
    out_dir = tmp_path / "out"

    result = run_wrapper(tmp_path, ghidra_home, out_dir)
    assert result.returncode == 9
    assert "FAKE_GHIDRA_HEADLESS_OK" in result.stderr
    assert not out_dir.exists()
    assert list(tmp_path.glob(".p1b-helper-setter-ghidra.*")) == []


def test_invalid_timeout_fails_before_project_open(tmp_path: Path) -> None:
    ghidra_home = make_fake_ghidra(tmp_path)
    out_dir = tmp_path / "out"

    result = run_wrapper(
        tmp_path,
        ghidra_home,
        out_dir,
        extra_env={"SHIFT_GHIDRA_HEADLESS_TIMEOUT_SECONDS": "0"},
    )
    assert result.returncode == 2
    assert "must be a positive integer" in result.stderr
    assert not out_dir.exists()


def test_wrapper_pins_readonly_isolated_export_and_fail_closed_publication_guard() -> None:
    source = RUNNER.read_text(encoding="utf-8")
    assert "-readOnly" in source
    assert "-noanalysis" in source
    assert "ShiftCompactInstructionStreamExporter.java" in source
    assert "COMPAT_SCRIPT_DIR=$(mktemp -d)" in source
    assert "output directory must be empty" in source
    assert "raw_executable_sha256_verified_in_this_run" in source
    assert "global_helper_non_vtable_indirect_setter_surface_complete" in source
    assert "manager_374_join_to_hdvehicle_4330_complete" in source
    assert "PUBLISHED=1" in source
