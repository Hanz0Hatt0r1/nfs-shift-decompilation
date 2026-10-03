# Retail memory-wrapper forwarding

The targeted Ghidra instruction export for the retail `SHIFT.exe` shows that the
five memory-wrapper functions use a mixture of ordinary `CALL` instructions and
terminal backend `JMP` tail calls.

This matters because a backend tail jump is still an argument-transfer boundary:
the wrapper prepares the backend's physical register/stack inputs and transfers
control without returning to the wrapper.  The original forwarding analyzer only
counted `CALL`, so it reported required backends as missing even though the raw
instruction export contained them as terminal `JMP` instructions.

## Retail forwarding shapes

The instruction-derived shapes are:

- `FUN_008868c0` -> tail `FUN_006382b0`
  - `ECX <- Stack[0x4]`
  - `EDX <- 0`
- `FUN_008868d0`
  - non-null branch -> `FUN_00638020`
    - `ECX <- Stack[0x8]`
    - `EDX <- Stack[0x4]`
    - stack arg <- `0`
  - fallback branch -> tail `FUN_006382b0`
    - `ECX <- Stack[0x4]`
    - `EDX <- 0`
- `FUN_00886900`
  - non-null branch -> `FUN_00638020`
    - `ECX <- Stack[0x8]`
    - `EDX <- Stack[0x4]`
    - stack arg <- `Stack[0xc]`
  - fallback branch -> tail `FUN_006382b0`
    - `ECX <- Stack[0x4]`
    - `EDX <- Stack[0xc]`
- `FUN_00886930` -> tail `thunk_FUN_0064f3a0`
  - `ECX <- Stack[0x4]`
  - `DL` is preserved from wrapper entry
- `FUN_00886950`
  - one branch -> tail `FUN_0064f260`
    - `ECX <- Stack[0x8]`
    - `EDX <- Stack[0x4]`
  - fallback branch -> tail `thunk_FUN_0064f3a0`
    - `ECX <- Stack[0x4]`
    - `DL` is preserved from wrapper entry

## Evidence boundary

These are physical forwarding relationships recovered from raw x86
instructions.  They do **not** by themselves prove semantic parameter names such
as byte count, pool id, alignment, delete kind, ownership state, or object type.

Ghidra's declared calling convention and parameter storage are retained as
metadata but are not promoted to semantic truth.  In particular, the release
wrappers overwrite working `ECX` from stack storage before the backend transfer,
so the instruction-derived forwarding is authoritative for this evidence layer.

`tools/ghidra/analyze_memory_wrapper_forwarding_retail.py` keeps the raw
instruction export unchanged.  It models only external terminal `JMP` transfers
to the already-known backend set as call-like data-flow boundaries and marks
those sites with `transfer_kind: tail-call` in the derived report.
