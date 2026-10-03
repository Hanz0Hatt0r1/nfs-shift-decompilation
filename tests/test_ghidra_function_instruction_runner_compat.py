import json
import os
import stat
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "tools" / "ghidra" / "run_shift_function_instructions.sh"
EXPORTER = ROOT / "tools" / "ghidra" / "ShiftFunctionInstructionExporter.java"


def test_exporter_avoids_ghidras_parse_address_override():
    source = EXPORTER.read_text(encoding="utf-8")
    assert "private Address parseTargetAddress(String token)" in source
    assert "Address address = parseTargetAddress(token);" in source
    assert "private Address parseAddress(String token)" not in source


def test_runner_uses_isolated_script_path(tmp_path):
    ghidra_home = tmp_path / "ghidra"
    support = ghidra_home / "support"
    support.mkdir(parents=True)
    capture = tmp_path / "capture.json"

    fake_headless = support / "analyzeHeadless"
    fake_headless.write_text(
        """#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

args = sys.argv[1:]
script_path = Path(args[args.index('-scriptPath') + 1])
post = args.index('-postScript')
script_name = args[post + 1]
out_file = Path(args[post + 2])
targets = args[post + 3:]

capture = Path(os.environ['SHIFT_TEST_CAPTURE'])
capture.write_text(json.dumps({
    'script_path': str(script_path),
    'script_name': script_name,
    'script_files': sorted(p.name for p in script_path.iterdir()),
}), encoding='utf-8')

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
            'format': 'SHIFT.GhidraFunctionInstructions/1',
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
            }],
        }
        handle.write(json.dumps(row) + '\\n')
""",
        encoding="utf-8",
    )
    fake_headless.chmod(fake_headless.stat().st_mode | stat.S_IXUSR)

    output = tmp_path / "out" / "instructions.jsonl"
    env = os.environ.copy()
    env["GHIDRA_HOME"] = str(ghidra_home)
    env["SHIFT_TEST_CAPTURE"] = str(capture)

    subprocess.run(
        [
            "bash",
            str(RUNNER),
            str(tmp_path / "project"),
            "shift",
            "SHIFT.exe",
            str(output),
            "FUN_00886900",
            "0x00886930",
        ],
        cwd=ROOT,
        env=env,
        check=True,
        text=True,
        capture_output=True,
    )

    observed = json.loads(capture.read_text(encoding="utf-8"))
    script_path = Path(observed["script_path"])
    assert observed["script_name"] == "ShiftFunctionInstructionExporter.java"
    assert observed["script_files"] == ["ShiftFunctionInstructionExporter.java"]
    assert script_path != ROOT / "tools" / "ghidra"
    # The runner removes the temporary script directory on exit.
    assert not script_path.exists()
    assert output.is_file()
