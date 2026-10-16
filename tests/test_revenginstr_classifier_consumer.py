from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "tools/ml/run_shift_cross_project_pcode_probe.sh"


def test_cross_project_runner_accepts_validated_generic_classifier_without_default_switch() -> None:
    text = RUNNER.read_text(encoding="utf-8")
    assert "REVENGINSTR_MODEL_DIR" in text
    assert "revenginstr.ml.selective" in text
    assert 'CLASSIFIED="$OUT_DIR/revenginstr-selective-transfer.jsonl"' in text
    assert 'GUARDED="$OUT_DIR/revenginstr-selective-transfer-foreign-guard.jsonl"' in text
    assert 'if [[ -n "${REVENGINSTR_MODEL_DIR:-}" ]]' in text
    assert 'elif [[ -n "${NEVERGONE_REPO:-}" ]]' in text
    assert "there is intentionally no unvalidated automatic model switch" in text


def test_cross_project_runner_shell_syntax() -> None:
    subprocess.run(["bash", "-n", str(RUNNER)], check=True)
