from __future__ import annotations

import sys
from pathlib import Path

from tools.replay_revenginstr_m23_call_return import replay, validate_frozen


def test_m23_call_return_paths_replay_from_pinned_pcode_exports() -> None:
    summary = validate_frozen()
    assert summary == {
        "source_file_count": 64,
        "source_rows": 7218,
        "source_files_with_paths": 11,
        "call_return_paths": 37,
        "functions_with_paths": 11,
        "paths_by_scan": {
            "screening-scan16": 18,
            "screening-scan17": 2,
            "screening-scan18": 17,
        },
        "paths_by_call_opcode": {"CALL": 28, "CALLIND": 9},
    }
    assert replay(Path(sys.executable).parent) == summary
