from __future__ import annotations

import sys
from pathlib import Path

from tools.replay_revenginstr_m23_load_return import replay, validate_frozen


def test_scan18_parameter_load_return_paths_replay_with_pinned_generic_tool() -> None:
    summary = validate_frozen()
    assert summary == {
        "parameter_load_rows_in_scan18": 115,
        "parameter_load_rows_for_function": 7,
        "load_return_paths": 3,
    }
    assert replay(Path(sys.executable).parent) == summary
