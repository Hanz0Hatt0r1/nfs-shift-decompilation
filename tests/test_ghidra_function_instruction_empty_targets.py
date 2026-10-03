import json
import os
import stat
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "tools" / "ghidra" / "run_shift_function_instructions.sh"


def _fake_ghidra_home(tmp_path: Path) -> Path:
    ghidra_home = tmp_path / "ghidra"
    support = ghidra_home / "support"
    support.mkdir(parents=True)
    fake_headless = support / "analyzeHeadless"
    fake_headless.write_text(
        """#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

Path(os.environ['SHIFT_TEST_CALLED']).write_text('yes', encoding='utf-8')
args = sys.argv[1:]
post = args.index('-postScript')
out_file = Path(args[post + 2])
targets = args[post + 3:]
Path(os.environ['SHIFT_TEST_TARGETS']).write_text(json.dumps(targets), encoding='utf-8')
out_file.parent.mkdir(parents=True, exist_ok=True)
with out_file.open('w', encoding='utf-8') as handle:
    for token in targets:
        value = token
        if value.lower().startswith('fun_'):
            value = value[4:]
        if value.lower().startswith('0x'):
            value = value[2:]
        address = '0x' + value.lower().zfill(8)
        row = {
            'format': 'SHIFT.GhidraFunctionInstructions/2',
            'program': 'SHIFT.exe',
            'requested': address,
            'found': True,
            'function': {
                'address': address,
                'name': 'FUN_' + value.lower().zfill(8),
                'size': 1,
                'calling_convention': '__cdecl',
            },
            'instruction_count': 1,
            'instructions': [{
                'address': address,
                'bytes': '90',
                'mnemonic': 'NOP',
                'text': 'NOP',
                'operands': [],
                'flow_type': 'FALL_THROUGH',
                'fallthrough': None,
                'flows': [],
                'references': [],
                'pcode': [],
            }],
        }
        handle.write(json.dumps(row) + '\\n')
""",
        encoding="utf-8",
    )
    fake_headless.chmod(fake_headless.stat().st_mode | stat.S_IXUSR)
    return ghidra_home


def test_runner_drops_blank_targets_before_headless(tmp_path):
    ghidra_home = _fake_ghidra_home(tmp_path)
    called = tmp_path / "called"
    observed_targets = tmp_path / "targets.json"
    output = tmp_path / "out.jsonl"
    env = os.environ.copy()
    env.update(
        GHIDRA_HOME=str(ghidra_home),
        SHIFT_TEST_CALLED=str(called),
        SHIFT_TEST_TARGETS=str(observed_targets),
        SHIFT_GHIDRA_HEADLESS_TIMEOUT_SECONDS="30",
    )

    completed = subprocess.run(
        [
            "bash",
            str(RUNNER),
            str(tmp_path / "project"),
            "shift",
            "SHIFT.exe",
            str(output),
            "",
            "   ",
            "FUN_00886900",
            "\t",
        ],
        cwd=ROOT,
        env=env,
        check=False,
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert called.is_file()
    assert json.loads(observed_targets.read_text(encoding="utf-8")) == ["FUN_00886900"]
    assert "ignored 3 empty function target(s)" in completed.stderr
    assert output.is_file()


def test_runner_rejects_all_blank_targets_before_headless(tmp_path):
    ghidra_home = _fake_ghidra_home(tmp_path)
    called = tmp_path / "called"
    observed_targets = tmp_path / "targets.json"
    env = os.environ.copy()
    env.update(
        GHIDRA_HOME=str(ghidra_home),
        SHIFT_TEST_CALLED=str(called),
        SHIFT_TEST_TARGETS=str(observed_targets),
        SHIFT_GHIDRA_HEADLESS_TIMEOUT_SECONDS="30",
    )

    completed = subprocess.run(
        [
            "bash",
            str(RUNNER),
            str(tmp_path / "project"),
            "shift",
            "SHIFT.exe",
            str(tmp_path / "out.jsonl"),
            "",
            "   ",
        ],
        cwd=ROOT,
        env=env,
        check=False,
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 2
    assert "no non-empty function targets were supplied" in completed.stderr
    assert "sed -n 'l'" in completed.stderr
    assert not called.exists()
