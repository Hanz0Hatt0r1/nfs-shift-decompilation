#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  bash tools/run_shift_capture_wine.sh --game /path/to/SHIFT.exe \
    --proxy /path/to/d3d9.dll [--d3dx9-41 /path/to/d3dx9_41.dll] [--output DIR] \
    [--mode passthrough|diagnostic|capture] [--debug-output] \
    [--frame-start N] [--frame-end N] \
    [--signature-discovery] \
    [--trigger] [--resource-trigger RULES] [--resource-trigger-repeat] \
    [--pre-frames N] [--post-frames N] \
    [--screenshots] [--buffer-payloads] [--texture-payloads] \
    [--wine wine] [-- GAME_ARGS...]

The launcher temporarily installs the proxy beside SHIFT.exe. If a local
d3d9.dll already exists (for example DXVK), it is staged as
"d3d9.shift_backend.dll" so the proxy chainloads the same renderer backend.
When --d3dx9-41 is supplied, the requested native D3DX DLL is staged into
the Wine prefix Windows DLL directory (syswow64 for WoW64, otherwise system32)
and forced with a native-only Wine DLL override.
EOF
}

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"

pe_machine() {
  python3 - "$1" <<'PY'
import struct
import sys

path = sys.argv[1]
try:
    with open(path, "rb") as f:
        if f.read(2) != b"MZ":
            raise ValueError("missing MZ header")
        f.seek(0x3C)
        raw = f.read(4)
        if len(raw) != 4:
            raise ValueError("truncated DOS header")
        pe_offset = struct.unpack("<I", raw)[0]
        f.seek(pe_offset)
        if f.read(4) != b"PE\0\0":
            raise ValueError("missing PE signature")
        raw = f.read(2)
        if len(raw) != 2:
            raise ValueError("truncated COFF header")
        print(f"0x{struct.unpack('<H', raw)[0]:04x}")
except Exception as exc:
    print(f"error:{exc}")
    sys.exit(1)
PY
}

pe_machine_name() {
  case "$1" in
    0x014c) printf '%s' "x86" ;;
    0x8664) printf '%s' "x64" ;;
    0xaa64) printf '%s' "arm64" ;;
    *) printf '%s' "$1" ;;
  esac
}

unix_to_wine_z_path() {
  python3 - "$1" <<'PY'
import os
import sys

path = os.path.abspath(sys.argv[1])
print("Z:" + path.replace("/", "\\"))
PY
}

to_wine_path() {
  if [[ -n "$winepath_command" ]]; then
    "$winepath_command" -w "$1"
  else
    unix_to_wine_z_path "$1"
  fi
}

is_shift_capture_proxy() {
  python3 - "$1" <<'PY'
import sys

with open(sys.argv[1], "rb") as stream:
    data = stream.read()
markers = (
    b"SHIFT_D3D9_CAPTURE_MODE",
    b"SHIFT_D3D9_CRASH_DIAGNOSTICS",
    b"proxy_d3d9_backend_selected",
)
raise SystemExit(0 if all(marker in data for marker in markers) else 1)
PY
}

ppdb_export_value() {
  python3 - "$1" "$2" <<'PY'
import shlex
import sys

path, wanted = sys.argv[1], sys.argv[2]
value = ""
with open(path, "r", encoding="utf-8", errors="replace") as stream:
    for raw in stream:
        try:
            parts = shlex.split(raw, comments=True, posix=True)
        except ValueError:
            continue
        if parts and parts[0] == "export":
            parts = parts[1:]
        for part in parts:
            if part.startswith(wanted + "="):
                value = part.split("=", 1)[1]
print(value)
PY
}

game=""
proxy=""
d3dx9_41=""
output="./shift-capture"
mode="diagnostic"
wine_command="${WINE_COMMAND:-wine}"
wine_command_explicit=0
winepath_command="${WINEPATH_COMMAND:-}"
debug_output=0
screenshots=0
frame_start=""
frame_end=""
trigger_capture=0
signature_discovery=0
resource_trigger=""
resource_trigger_repeat=0
pre_frames=2
post_frames=2
buffer_payloads=0
texture_payloads=0
game_args=()

while (($#)); do
  case "$1" in
    --game) game="${2:?missing value for --game}"; shift 2 ;;
    --proxy) proxy="${2:?missing value for --proxy}"; shift 2 ;;
    --d3dx9-41) d3dx9_41="${2:?missing value for --d3dx9-41}"; shift 2 ;;
    --output) output="${2:?missing value for --output}"; shift 2 ;;
    --mode) mode="${2:?missing value for --mode}"; shift 2 ;;
    --wine) wine_command="${2:?missing value for --wine}"; wine_command_explicit=1; shift 2 ;;
    --debug-output) debug_output=1; shift ;;
    --frame-start) frame_start="${2:?missing value for --frame-start}"; shift 2 ;;
    --frame-end) frame_end="${2:?missing value for --frame-end}"; shift 2 ;;
    --signature-discovery) signature_discovery=1; shift ;;
    --trigger) trigger_capture=1; shift ;;
    --resource-trigger) resource_trigger="${2:?missing value for --resource-trigger}"; trigger_capture=1; shift 2 ;;
    --resource-trigger-repeat) resource_trigger_repeat=1; trigger_capture=1; shift ;;
    --pre-frames) pre_frames="${2:?missing value for --pre-frames}"; shift 2 ;;
    --post-frames) post_frames="${2:?missing value for --post-frames}"; shift 2 ;;
    --screenshots) screenshots=1; shift ;;
    --buffer-payloads) buffer_payloads=1; shift ;;
    --texture-payloads) texture_payloads=1; shift ;;
    --) shift; game_args=("$@"); break ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if [[ -z "$game" || -z "$proxy" ]]; then
  usage >&2
  exit 2
fi

case "$mode" in
  passthrough|diagnostic|capture) ;;
  *) echo "invalid --mode: $mode" >&2; exit 2 ;;
esac

for bound in "$frame_start" "$frame_end"; do
  if [[ -n "$bound" && ! "$bound" =~ ^[0-9]+$ ]]; then
    echo "frame bounds must be non-negative integers" >&2
    exit 2
  fi
done
if [[ -n "$frame_start" && -n "$frame_end" ]] && ((frame_end < frame_start)); then
  echo "--frame-end must be >= --frame-start" >&2
  exit 2
fi
for count in "$pre_frames" "$post_frames"; do
  if [[ ! "$count" =~ ^[0-9]+$ ]]; then
    echo "trigger frame counts must be non-negative integers" >&2
    exit 2
  fi
done
if ((trigger_capture)) && [[ -n "$frame_start" || -n "$frame_end" ]]; then
  echo "--trigger/--resource-trigger cannot be combined with --frame-start/--frame-end" >&2
  exit 2
fi
if ((signature_discovery)) && { ((trigger_capture)) || [[ -n "$frame_start" || -n "$frame_end" ]]; }; then
  echo "--signature-discovery cannot be combined with frame or trigger capture" >&2
  exit 2
fi

if ((signature_discovery)); then
  mode="capture"
fi

command -v python3 >/dev/null 2>&1 || {
  echo "python3 is required to validate PE architecture" >&2
  exit 2
}

game="$(realpath "$game")"
proxy="$(realpath "$proxy")"
if [[ -n "$d3dx9_41" ]]; then
  d3dx9_41="$(realpath "$d3dx9_41")"
fi
output="$(realpath -m "$output")"

[[ -f "$game" ]] || { echo "game not found: $game" >&2; exit 2; }
[[ -f "$proxy" ]] || { echo "proxy not found: $proxy" >&2; exit 2; }
game_machine="$(pe_machine "$game")" || {
  echo "failed to read PE architecture: $game" >&2
  exit 2
}
if [[ -n "$d3dx9_41" ]]; then
  [[ -f "$d3dx9_41" ]] || { echo "d3dx9_41.dll not found: $d3dx9_41" >&2; exit 2; }
  d3dx_machine="$(pe_machine "$d3dx9_41")" || {
    echo "failed to read PE architecture: $d3dx9_41" >&2
    exit 2
  }
  if [[ "$d3dx_machine" != "$game_machine" ]]; then
    echo "d3dx9_41.dll architecture mismatch:" >&2
    echo "  game : $(pe_machine_name "$game_machine") ($game_machine) $game" >&2
    echo "  d3dx : $(pe_machine_name "$d3dx_machine") ($d3dx_machine) $d3dx9_41" >&2
    echo "SHIFT requires a d3dx9_41.dll with the same PE architecture as SHIFT.exe." >&2
    exit 2
  fi
fi
[[ "${proxy##*/}" == "d3d9.dll" ]] || {
  echo "proxy must be named d3d9.dll" >&2
  exit 2
}

game_dir="${game%/*}"
target_dll="$game_dir/d3d9.dll"
sidecar_dll="$game_dir/d3d9.shift_backend.dll"

wine_prefix=""
if [[ "$game" == */drive_c/* ]]; then
  wine_prefix="${game%%/drive_c/*}"
elif [[ -n "${WINEPREFIX:-}" ]]; then
  wine_prefix="$(realpath -m "$WINEPREFIX")"
else
  wine_prefix="$(realpath -m "$HOME/.wine")"
fi

# Keep every Wine-facing operation on the exact same prefix. Without this,
# staging a native DLL into an inferred PortProton prefix while wine/winepath
# silently use ~/.wine makes the loader report the staged DLL as missing.
export WINEPREFIX="$wine_prefix"

portproton_root=""
portproton_wine_use=""
portproton_wine_auto=""
portproton_start=""
use_portproton_start=0
ppdb=""
if [[ "$wine_prefix" == */PortProton/data/prefixes/* ]]; then
  portproton_root="${wine_prefix%%/data/prefixes/*}"
  ppdb="$game.ppdb"
  portproton_start="$portproton_root/data/scripts/start.sh"
  if [[ -f "$ppdb" ]]; then
    portproton_wine_use="$(ppdb_export_value "$ppdb" PW_WINE_USE)"
    if (( ! wine_command_explicit )) && [[ -f "$portproton_start" ]]; then
      use_portproton_start=1
    fi
  fi
  if (( ! wine_command_explicit )) && [[ -n "$portproton_wine_use" ]]; then
    for candidate in \
      "$portproton_root/data/dist/$portproton_wine_use/bin/wine" \
      "$portproton_root/data/dist/$portproton_wine_use/files/bin/wine"; do
      if [[ -x "$candidate" ]]; then
        wine_command="$candidate"
        portproton_wine_auto="$candidate"
        break
      fi
    done
  fi
fi

command -v "$wine_command" >/dev/null 2>&1 || {
  echo "Wine executable not found: $wine_command" >&2
  exit 2
}
wine_resolved="$(command -v "$wine_command")"

if [[ -z "$winepath_command" ]]; then
  sibling_winepath="${wine_resolved%/*}/winepath"
  if [[ -x "$sibling_winepath" ]]; then
    winepath_command="$sibling_winepath"
  fi
fi
if [[ -n "$winepath_command" ]]; then
  command -v "$winepath_command" >/dev/null 2>&1 || {
    echo "winepath executable not found: $winepath_command" >&2
    exit 2
  }
  winepath_resolved="$(command -v "$winepath_command")"
else
  winepath_resolved="internal Z: path mapping"
fi

target_d3dx=""
if [[ -n "$d3dx9_41" ]]; then
  if [[ "$game_machine" == "0x014c" && -d "$wine_prefix/drive_c/windows/syswow64" ]]; then
    target_d3dx="$wine_prefix/drive_c/windows/syswow64/d3dx9_41.dll"
  else
    target_d3dx="$wine_prefix/drive_c/windows/system32/d3dx9_41.dll"
  fi
fi

if [[ "$proxy" == "$target_dll" ]]; then
  echo "--proxy must point to the built artifact, not the game's d3d9.dll" >&2
  exit 2
fi

d3dx_same_file=0
if [[ -n "$d3dx9_41" && -e "$target_d3dx" && "$d3dx9_41" -ef "$target_d3dx" ]]; then
  d3dx_same_file=1
fi

mkdir -p "$output"
capture_path="$output/shift_d3d9_capture.jsonl"
crash_path="$output/shift_d3d9_crash.jsonl"
backup_dll="$output/original_d3d9.dll"
backup_sidecar="$output/original_d3d9.shift_backend.dll"
backup_d3dx="$output/original_d3dx9_41.dll"
backup_ppdb="$output/original_SHIFT.exe.ppdb"
stale_dll="$output/stale_capture_d3d9.dll"
stale_sidecar="$output/stale_capture_d3d9.shift_backend.dll"

# Every launcher invocation represents one capture session. The native writer
# appends by design, so clear launcher-owned outputs here to avoid mixing
# different process runs when an output directory is reused.
rm -f "$capture_path" "$crash_path" "$output/resource_signatures.json" "$output/capture.trigger" \
  "$stale_dll" "$stale_sidecar"
if ((screenshots)); then rm -rf "$output/frames"; fi
if ((buffer_payloads)); then rm -rf "$output/buffers"; fi
if ((texture_payloads)); then rm -rf "$output/texture-payloads"; fi

had_dll=0
had_sidecar=0
had_d3dx=0
d3dx_mutated=0
staged_backend=0
stale_target_proxy=0
stale_sidecar_proxy=0
ppdb_mutated=0

# Make every recovery copy before changing the game directory. Never preserve
# an older SHIFT capture proxy as the renderer backend: that creates
# proxy->proxy chainloading and installs two crash handlers in one process.
if [[ -f "$target_dll" ]]; then
  if is_shift_capture_proxy "$target_dll"; then
    cp -f "$target_dll" "$stale_dll"
    stale_target_proxy=1
  else
    cp -f "$target_dll" "$backup_dll"
    had_dll=1
  fi
fi
if [[ -f "$sidecar_dll" ]]; then
  if is_shift_capture_proxy "$sidecar_dll"; then
    cp -f "$sidecar_dll" "$stale_sidecar"
    stale_sidecar_proxy=1
  else
    cp -f "$sidecar_dll" "$backup_sidecar"
    had_sidecar=1
  fi
fi
if [[ -n "$d3dx9_41" ]] && (( ! d3dx_same_file )) && [[ -f "$target_d3dx" ]]; then
  cp -f "$target_d3dx" "$backup_d3dx"
  had_d3dx=1
fi
if ((use_portproton_start)); then
  cp -p "$ppdb" "$backup_ppdb"
fi

restore() {
  local rc=$?
  trap - EXIT INT TERM
  if ((had_dll)); then
    cp -f "$backup_dll" "$target_dll"
  else
    rm -f "$target_dll"
  fi
  if ((had_sidecar)); then
    cp -f "$backup_sidecar" "$sidecar_dll"
  else
    rm -f "$sidecar_dll"
  fi
  if ((d3dx_mutated)); then
    if ((had_d3dx)); then
      cp -f "$backup_d3dx" "$target_d3dx"
    else
      rm -f "$target_d3dx"
    fi
  fi
  if ((ppdb_mutated)); then
    cp -p "$backup_ppdb" "$ppdb"
  fi
  exit "$rc"
}
trap restore EXIT INT TERM

if ((stale_sidecar_proxy)); then
  rm -f "$sidecar_dll"
fi

if ((had_dll)); then
  # A genuine game-local renderer (for example DXVK) takes precedence over any
  # pre-existing sidecar for this capture session.
  rm -f "$sidecar_dll"
  if [[ "$(sha256sum "$target_dll" | awk '{print $1}')" != \
        "$(sha256sum "$proxy" | awk '{print $1}')" ]]; then
    cp -f "$target_dll" "$sidecar_dll"
    staged_backend=1
  fi
elif ((had_sidecar)); then
  # A previous interrupted launch may have left the genuine renderer in the
  # sidecar while d3d9.dll itself is a stale capture proxy. Keep that renderer.
  staged_backend=1
else
  rm -f "$sidecar_dll"
fi

cp -f "$proxy" "$target_dll"
if [[ -n "$d3dx9_41" ]] && (( ! d3dx_same_file )); then
  mkdir -p "${target_d3dx%/*}"
  cp -f "$d3dx9_41" "$target_d3dx"
  d3dx_mutated=1
fi

capture_windows="$(to_wine_path "$capture_path")"
crash_windows="$(to_wine_path "$crash_path")"
export SHIFT_D3D9_CAPTURE="$capture_windows"
export SHIFT_D3D9_CRASH_LOG="$crash_windows"
export SHIFT_D3D9_CRASH_DIAGNOSTICS=1
export SHIFT_D3D9_CAPTURE_MODE="$mode"
unset SHIFT_D3D9_BACKEND || true

if ((signature_discovery)); then
  export SHIFT_D3D9_CAPTURE_SIGNATURE_DISCOVERY=1
else
  unset SHIFT_D3D9_CAPTURE_SIGNATURE_DISCOVERY || true
fi

if [[ -n "$frame_start" ]]; then
  export SHIFT_D3D9_CAPTURE_FRAME_START="$frame_start"
else
  unset SHIFT_D3D9_CAPTURE_FRAME_START || true
fi
if [[ -n "$frame_end" ]]; then
  export SHIFT_D3D9_CAPTURE_FRAME_END="$frame_end"
else
  unset SHIFT_D3D9_CAPTURE_FRAME_END || true
fi

trigger_file="$output/capture.trigger"
if ((trigger_capture)); then
  rm -f "$trigger_file"
  export SHIFT_D3D9_CAPTURE_TRIGGER=1
  export SHIFT_D3D9_CAPTURE_TRIGGER_PRE_FRAMES="$pre_frames"
  export SHIFT_D3D9_CAPTURE_TRIGGER_POST_FRAMES="$post_frames"
  export SHIFT_D3D9_CAPTURE_TRIGGER_KEY=0x79
  export SHIFT_D3D9_CAPTURE_TRIGGER_FILE="$(to_wine_path "$trigger_file")"
  if [[ -n "$resource_trigger" ]]; then
    export SHIFT_D3D9_CAPTURE_RESOURCE_TRIGGER="$resource_trigger"
  else
    unset SHIFT_D3D9_CAPTURE_RESOURCE_TRIGGER || true
  fi
  if ((resource_trigger_repeat)); then
    export SHIFT_D3D9_CAPTURE_RESOURCE_TRIGGER_REPEAT=1
  else
    unset SHIFT_D3D9_CAPTURE_RESOURCE_TRIGGER_REPEAT || true
  fi
else
  unset SHIFT_D3D9_CAPTURE_TRIGGER || true
  unset SHIFT_D3D9_CAPTURE_TRIGGER_PRE_FRAMES || true
  unset SHIFT_D3D9_CAPTURE_TRIGGER_POST_FRAMES || true
  unset SHIFT_D3D9_CAPTURE_TRIGGER_KEY || true
  unset SHIFT_D3D9_CAPTURE_TRIGGER_FILE || true
  unset SHIFT_D3D9_CAPTURE_RESOURCE_TRIGGER || true
  unset SHIFT_D3D9_CAPTURE_RESOURCE_TRIGGER_REPEAT || true
fi

if ((debug_output)); then
  export SHIFT_D3D9_CAPTURE_DEBUG_OUTPUT=1
else
  unset SHIFT_D3D9_CAPTURE_DEBUG_OUTPUT || true
fi

if ((screenshots)); then
  frame_dir="$output/frames"
  mkdir -p "$frame_dir"
  export SHIFT_D3D9_CAPTURE_SCREENSHOT=1
  export SHIFT_D3D9_CAPTURE_SCREENSHOT_EVERY=1
  export SHIFT_D3D9_CAPTURE_SCREENSHOT_DIR="$(to_wine_path "$frame_dir")"
fi

if ((buffer_payloads)); then
  buffer_dir="$output/buffers"
  mkdir -p "$buffer_dir"
  export SHIFT_D3D9_CAPTURE_BUFFER_PAYLOADS=1
  export SHIFT_D3D9_CAPTURE_BUFFER_PAYLOAD_DIR="$(to_wine_path "$buffer_dir")"
else
  unset SHIFT_D3D9_CAPTURE_BUFFER_PAYLOADS || true
  unset SHIFT_D3D9_CAPTURE_BUFFER_PAYLOAD_DIR || true
fi

if ((texture_payloads)); then
  texture_payload_dir="$output/texture-payloads"
  mkdir -p "$texture_payload_dir"
  export SHIFT_D3D9_CAPTURE_TEXTURE_PAYLOADS=1
  export SHIFT_D3D9_CAPTURE_TEXTURE_PAYLOAD_DIR="$(to_wine_path "$texture_payload_dir")"
else
  unset SHIFT_D3D9_CAPTURE_TEXTURE_PAYLOADS || true
  unset SHIFT_D3D9_CAPTURE_TEXTURE_PAYLOAD_DIR || true
fi

old_overrides="${WINEDLLOVERRIDES:-}"
if ((use_portproton_start)); then
  ppdb_overrides="$(ppdb_export_value "$ppdb" WINEDLLOVERRIDES)"
  if [[ -n "$ppdb_overrides" ]]; then
    old_overrides="$ppdb_overrides"
  fi
fi
filtered_overrides=""
if [[ -n "$old_overrides" ]]; then
  IFS=';' read -r -a override_parts <<< "$old_overrides"
  for entry in "${override_parts[@]}"; do
    [[ -n "$entry" ]] || continue
    name="${entry%%=*}"
    if [[ "${name,,}" == "d3d9" || "${name,,}" == "d3dx9_41" ]]; then
      continue
    fi
    if [[ -n "$filtered_overrides" ]]; then
      filtered_overrides+=";"
    fi
    filtered_overrides+="$entry"
  done
fi
if [[ -n "$filtered_overrides" ]]; then
  export WINEDLLOVERRIDES="$filtered_overrides;d3d9=n,b;d3dx9_41=n"
else
  export WINEDLLOVERRIDES="d3d9=n,b;d3dx9_41=n"
fi

if ((use_portproton_start)); then
  python3 - "$ppdb" <<'PY'
import os
import shlex
import sys

path = sys.argv[1]
with open(path, "a", encoding="utf-8") as stream:
    stream.write("\n# SHIFT_CAPTURE_TEMP_BEGIN\n")
    stream.write("export PW_GUI_DISABLED_CS=1\n")
    stream.write("export PW_NO_AUTO_CREATE_SHORTCUT=1\n")
    # Capture must bypass gamescope. PortProton may report gamescope as broken
    # yet still keep PW_GAMESCOPE=1 from the saved profile, causing the primary
    # child to exit before SHIFT reaches Direct3DCreate9.
    stream.write("export PW_GAMESCOPE=0\n")
    for name in sorted(os.environ):
        if name.startswith("SHIFT_D3D9_"):
            stream.write(f"export {name}={shlex.quote(os.environ[name])}\n")
    stream.write(
        "export WINEDLLOVERRIDES="
        + shlex.quote(os.environ.get("WINEDLLOVERRIDES", ""))
        + "\n"
    )
    stream.write("# SHIFT_CAPTURE_TEMP_END\n")
PY
  ppdb_mutated=1
fi

echo "Launching: $game"
echo "WINEPREFIX: $WINEPREFIX"
echo "Wine exe : $wine_resolved"
echo "Winepath : $winepath_resolved"
if [[ "$winepath_resolved" == "internal Z: path mapping" ]]; then
  echo "Path map : avoiding external winepath/wineserver startup"
fi
if [[ -n "$portproton_wine_auto" ]]; then
  echo "Runtime : auto-selected from PW_WINE_USE=$portproton_wine_use"
fi
if ((use_portproton_start)); then
  echo "Launcher: $portproton_start"
  echo "PPDB    : temporary capture exports installed; original will be restored"
  echo "Gamescope: disabled for capture session"
fi
if [[ -n "$portproton_root" && "$wine_resolved" != "$portproton_root/"* ]]; then
  echo "warning: PortProton prefix is being launched with Wine outside the PortProton tree: $wine_resolved" >&2
  if [[ -n "$portproton_wine_use" ]]; then
    echo "PortProton PW_WINE_USE: $portproton_wine_use" >&2
  fi
  echo "         use --wine with the Wine/Proton binary selected by PortProton if early startup is unstable" >&2
fi
echo "Capture : $capture_path"
echo "Crash   : $crash_path"
echo "Mode    : $mode"
echo "DLL ovrd: d3d9=n,b; d3dx9_41=n"
if [[ -n "$d3dx9_41" ]]; then
  echo "Prefix  : $wine_prefix"
  echo "PE arch : game=$(pe_machine_name "$game_machine") d3dx=$(pe_machine_name "$d3dx_machine")"
  echo "D3DX9   : $d3dx9_41 -> $target_d3dx"
  if ((d3dx_same_file)); then
    echo "D3DX9   : source already resolves to the Wine prefix DLL; no copy needed"
  else
    echo "D3DX9   : staged temporarily; original prefix DLL will be restored"
  fi
  echo "D3DX9 sha256: $(sha256sum "$target_d3dx" | awk '{print $1}')"
else
  echo "D3DX9   : no explicit source DLL supplied"
fi
if ((signature_discovery)); then
  echo "Discover: compact resource-signature pass"
fi
if [[ -n "$frame_start" || -n "$frame_end" ]]; then
  echo "Frames  : ${frame_start:-0}..${frame_end:-end}"
fi
if ((trigger_capture)); then
  echo "Trigger : F10 (pre=$pre_frames, post=$post_frames)"
  echo "          or: touch $trigger_file"
  if [[ -n "$resource_trigger" ]]; then
    echo "Resource: $resource_trigger"
    if ((resource_trigger_repeat)); then echo "Repeat  : enabled"; fi
  fi
fi
if ((buffer_payloads)); then echo "Buffers : $buffer_dir"; fi
if ((texture_payloads)); then echo "Tex raw : $texture_payload_dir"; fi
if ((stale_target_proxy)); then
  echo "Stale   : archived old SHIFT capture proxy as $stale_dll"
fi
if ((stale_sidecar_proxy)); then
  echo "Stale   : archived old SHIFT capture sidecar as $stale_sidecar"
fi
if ((staged_backend)); then
  if ((had_dll)); then
    echo "Backend : preserved local renderer via $sidecar_dll"
  else
    echo "Backend : preserved existing non-proxy sidecar $sidecar_dll"
  fi
else
  echo "Backend : Wine/system d3d9.dll"
fi

set +e
if ((use_portproton_start)); then
  (
    cd "$game_dir"
    bash "$portproton_start" "$game" "${game_args[@]}"
  )
  exit_code=$?
else
  (
    cd "$game_dir"
    "$wine_command" "$game" "${game_args[@]}"
  )
  exit_code=$?
fi
set -e

if ((exit_code != 0)); then
  echo "warning: game exited with code $exit_code; diagnostic prefix may still be useful" >&2
fi

if [[ ! -f "$capture_path" ]]; then
  echo "no runtime capture was produced: $capture_path" >&2
  exit 3
fi

python3 "$repo_root/native_capture/analyze_proxy_log.py" "$capture_path" 2>/dev/null || true
if ((signature_discovery)); then
  python3 "$repo_root/tools/list_d3d9_resource_signatures.py" \
    "$capture_path" --top 100 --json "$output/resource_signatures.json" || true
fi
if [[ -s "$crash_path" ]]; then
  python3 "$repo_root/native_capture/analyze_proxy_crash.py" "$crash_path" 2>/dev/null || true
  echo "Crash context: $crash_path"
fi
echo "Capture completed: $capture_path"
exit "$exit_code"
