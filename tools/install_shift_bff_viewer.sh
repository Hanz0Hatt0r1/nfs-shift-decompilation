#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PREFIX=${PREFIX:-$HOME/.local}
mkdir -p "$PREFIX/bin"
cat > "$PREFIX/bin/shift-bff-viewer" <<EOF
#!/bin/sh
exec python3 "$ROOT/tools/shift_bff_viewer.py" gui "\$@"
EOF
chmod +x "$PREFIX/bin/shift-bff-viewer"
echo "Installed: $PREFIX/bin/shift-bff-viewer"
