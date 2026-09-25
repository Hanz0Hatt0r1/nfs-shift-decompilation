import struct
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _minimal_mode2_bab() -> bytes:
    payload = (
        struct.pack("<IIII", 0, 0, 0, 0)
        + struct.pack("<III", 0, 0, 0)
        + struct.pack("<I", 0)
        + struct.pack("<I", 0)
    )
    # parse_bab() needs the verified BAB header and one aligned name.
    header = bytearray(0x30)
    header[0:4] = b"BAB\0"
    header[4:8] = struct.pack("<I", 1)
    header[8:12] = struct.pack("<I", 0)
    # The common animation payload starts at 0x30 for an empty BAB name.
    header[0x20:0x24] = struct.pack("<I", 0)
    return bytes(header) + payload


def test_bab_animation_runtime_cli(tmp_path):
    bab = tmp_path / "empty.bab"
    output = tmp_path / "runtime.json"
    bab.write_bytes(_minimal_mode2_bab())
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "shift_importer.py"),
            "bab-animation-runtime",
            str(bab),
            str(output),
            "--mode",
            "2",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert '"ready": true' in proc.stdout
    report = output.read_text(encoding="utf-8")
    assert '"format": "SHIFT.BABAnimationRuntime/1"' in report
    assert '"status": "decoded"' in report
