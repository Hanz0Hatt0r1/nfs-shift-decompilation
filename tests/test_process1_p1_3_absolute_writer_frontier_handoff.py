from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/PROCESS_1_P1_3_ABSOLUTE_WRITER_FRONTIER_HANDOFF.md"


def test_absolute_writer_handoff_keeps_provider_count_and_gate() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert "FUN_00791020" in text
    assert "+0x938/+0x13b8/+0x1e38/+0x28b8" in text
    assert "Provider count remains 7" in text
    assert "P1.3 remains incomplete" in text
