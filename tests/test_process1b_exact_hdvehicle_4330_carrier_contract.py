from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[1]
THREAD = ROOT / "tools" / "ghidra" / "analyze_p1b_hdvehicle_4330_thread_start_surface.py"
NONTHREAD = ROOT / "tools" / "ghidra" / "analyze_p1b_hdvehicle_4330_nonthread_callback_frontier.py"

EXPECTED = {
    0x00769520, 0x0076B130, 0x0076DF50, 0x00768A4D, 0x00756050,
    0x00772200, 0x00772570, 0x007C3B00, 0x0076B280, 0x007618F0,
    0x00769640, 0x007567A0, 0x00756BB0, 0x00771DB0, 0x00771E10,
}

P1D_ONLY_SENTINELS = {
    0x00758B50,
    0x00760B50,
    0x00763570,
    0x00755F80,
}


def test_thread_analyzer_uses_canonical_p1b_exact_carriers():
    namespace = runpy.run_path(str(THREAD), run_name="p1b_thread_contract")
    assert namespace["EXACT_CARRIERS"] == EXPECTED
    assert namespace["EXACT_CARRIERS"].isdisjoint(P1D_ONLY_SENTINELS)


def test_nonthread_analyzer_uses_same_canonical_p1b_exact_carriers():
    namespace = runpy.run_path(str(NONTHREAD), run_name="p1b_nonthread_contract")
    got = {int(value, 16) for value in namespace["CARRIERS"]}
    assert got == EXPECTED
    assert got.isdisjoint(P1D_ONLY_SENTINELS)
