from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "tools" / "run_bmw_d3d9_buffer_capture.sh"


def test_bmw_capture_launcher_is_valid_bash():
    result = subprocess.run(["bash", "-n", str(LAUNCHER)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_bmw_capture_launcher_enables_only_required_capture_modes():
    text = LAUNCHER.read_text(encoding="utf-8")
    assert 'export SHIFT_D3D9_CAPTURE_BUFFER_PAYLOADS=1' in text
    assert 'export SHIFT_D3D9_CAPTURE_BUFFER_PAYLOAD_DIR="$PAYLOAD_DIR"' in text
    assert 'export SHIFT_D3D9_CAPTURE_SCREENSHOT="${SHIFT_D3D9_CAPTURE_SCREENSHOT:-0}"' in text
    assert 'export SHIFT_D3D9_CAPTURE_TEXTURE_SNAPSHOT="${SHIFT_D3D9_CAPTURE_TEXTURE_SNAPSHOT:-0}"' in text
    assert 'exec "$WINE_BIN" "$GAME_EXE" "${GAME_ARGS[@]}"' in text
    assert 'WINEDLLOVERRIDES="d3d9=n' in text


def test_bmw_capture_launcher_uses_dedicated_output_subdirectory():
    text = LAUNCHER.read_text(encoding="utf-8")
    assert 'PAYLOAD_DIR="$OUTPUT_DIR/buffer_payloads"' in text
    assert 'SHIFT_D3D9_CAPTURE="$OUTPUT_DIR/shift_d3d9_capture.jsonl"' in text
