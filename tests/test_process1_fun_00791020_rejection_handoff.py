from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/PROCESS_1_FUN_00791020_REJECTION_HANDOFF.md"


def test_rejection_handoff_is_explicit() -> None:
    text = DOC.read_text(encoding="utf-8")
    for token in (
        "BLOCKER:",
        "INPUT:",
        "OUTPUT:",
        "CONSUMER:",
        "GATES_CHANGED:",
        "LIMITS:",
        "TESTS:",
        "NEXT_OWNER:",
        "NEXT_STEP:",
        "Provider count remains 7",
    ):
        assert token in text
