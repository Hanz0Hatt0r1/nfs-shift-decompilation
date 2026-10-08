from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "evidence/process1_fun_00791020_rejection_next_step.md"


def test_next_step_keeps_absolute_hdvehicle_writer_search_fail_closed() -> None:
    text = DOC.read_text(encoding="utf-8")
    for token in (
        "HDVehicle+0x938/+0x13b8/+0x1e38/+0x28b8",
        "receiver/base alias to selected `HDVehicle`",
        "numeric subobject offsets alone are navigation evidence only",
        "Provider count remains 7",
        "P1.3 remains incomplete",
    ):
        assert token in text
