import os
import re
import subprocess
from pathlib import Path


EXPECTED_TARGETS = [
    "FUN_008868c0",
    "FUN_008868d0",
    "FUN_00886900",
    "FUN_00886930",
    "FUN_00886950",
]


def _script() -> Path:
    return (
        Path(__file__).resolve().parents[1]
        / "tools"
        / "ghidra"
        / "run_memory_wrapper_forwarding.sh"
    )


def test_runner_is_executable_and_pins_retail_wrapper_set():
    script = _script()
    assert os.access(script, os.X_OK)
    text = script.read_text(encoding="utf-8")

    match = re.search(r"TARGETS=\(\n(?P<body>.*?)\n\)", text, re.DOTALL)
    assert match is not None
    targets = [line.strip() for line in match.group("body").splitlines() if line.strip()]
    assert targets == EXPECTED_TARGETS

    assert 'run_shift_function_instructions.sh"' in text
    assert 'analyze_memory_wrapper_forwarding.py"' in text
    assert 'memory_wrapper_instructions.jsonl' in text
    assert 'memory_wrapper_forwarding.json' in text


def test_runner_usage_fails_before_requiring_ghidra():
    result = subprocess.run(
        [str(_script())],
        text=True,
        capture_output=True,
        check=False,
        env={key: value for key, value in os.environ.items() if key != "GHIDRA_HOME"},
    )
    assert result.returncode == 2
    assert "Usage:" in result.stderr
    assert "GHIDRA_HOME" not in result.stderr
