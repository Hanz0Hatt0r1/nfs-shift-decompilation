#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: $0 <libnfs_shift_pcode_partial.so>" >&2
  exit 2
fi

ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
CC=${CC:-cc}
TEMP_DIR=$(mktemp -d)
trap 'rm -rf "$TEMP_DIR"' EXIT

"$CC" -std=c11 -O2 -Wall -Wextra -Werror \
  -I "$ROOT/native_runtime/include" \
  "$ROOT/tools/ghidra/smoke_shift_pcode_elf.c" -ldl \
  -o "$TEMP_DIR/smoke_shift_pcode_elf"
"$TEMP_DIR/smoke_shift_pcode_elf" "$1"
