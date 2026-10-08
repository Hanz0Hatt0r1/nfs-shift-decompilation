from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/PROCESS_1_P1_3_ABSOLUTE_WRITER_FRONTIER.md"


def test_absolute_writer_frontier_requires_selected_hdvehicle_receiver() -> None:
    text = DOC.read_text(encoding="utf-8")
    for token in (
        "HDVehicle+0x938",
        "HDVehicle+0x13b8",
        "HDVehicle+0x1e38",
        "HDVehicle+0x28b8",
        "receiver/base is independently proven to alias selected `HDVehicle`",
        "Matching a raw `+0x538` or `+0x938` literal",
        "Provider count remains 7",
    ):
        assert token in text
