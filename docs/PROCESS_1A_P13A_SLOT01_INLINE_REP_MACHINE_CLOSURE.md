# Process 1A / P1.3A — shallow inline REP copy/init closure

## Scope

Slot0 `HDVehicle+0x938` and slot1 `HDVehicle+0x13b8` still require selected-root alias/callee/bulk-copy closure. The named memory-family frontier and same-function wheel-topology subset are already bounded, but compiler-generated inline copies or clears can avoid `memcpy`/`memset` symbols entirely.

This slice bounds one concrete machine class: `REP MOVS*` and `REP STOS*` instructions reachable within four direct callgraph edges of the four recovered wheel/physics roots.

## Inventory

`tools/ghidra/analyze_p1a_slot01_inline_rep_frontier.py` hash-locks both the PC retail 1.02 executable and the Drive Ghidra SQLite index, disassembles the retail image with `objdump`, maps REP sites back into sized Ghidra functions, and joins those functions to shortest direct-call paths.

Retail result:

- 822 `REP MOVS/STOS` instruction sites in the disassembly;
- 735 sites map into 466 sized Ghidra functions;
- exactly 5 distinct REP-bearing functions occur within depth 4 of the P1.3A roots.

The five functions are `FUN_00764266`, `FUN_00887580`, `FUN_00634240`, `FUN_007b7840`, and `FUN_00886e10`.

## Adjudication

`FUN_00764266` is a stack clear. `0x0076425f` zeros EAX; the unique thunk loads `ECX=0x54`; `0x00764266` sets `EDI=EBP-0x320`; `0x0076426c` clears exactly `0x150` bytes of the caller stack frame.

`FUN_00634240` appends bytes into the fixed image-global message buffer rooted at `0x00bf9b30`. Its four REP sites never use a selected-HDVehicle-derived destination.

`FUN_007b7840` copies eight dwords from `EBP-0xb0` to `EBP-0x180`, so its REP operation is strictly stack-to-stack.

`FUN_00887580` is the important numeric-collision case. `FUN_00887720` constructs and returns the exact singleton `0x00c29640`; the constructor installs vptr `0x00b20a90`. It then clears `[receiver+0x3a0, receiver+0x558)` with `REP STOSD`. This range **does include numeric local offset `+0x538`**, but the receiver is the fixed singleton, not selected HDVehicle wheel storage. Numeric overlap is therefore rejected as identity evidence.

`FUN_00886e10` is called on that singleton's nested `+0x70c` object, exact address `0x00c29d4c`. Its 20 REP copies initialize 0x1c-byte records ending at nested `+0x230`; it is a separate fixed receiver domain.

## Gate

```text
shallow REP depth<=4 surface complete          = true
shallow REP candidates                         = 5
shallow REP candidates rejected                = 5
selected-HDVehicle writer found in this subset = false
all inline/custom copies ruled out             = false
indirect copy dispatch ruled out               = false
deep direct paths ruled out                    = false
slot0 complete                                 = false
slot1 complete                                 = false
P1.3 complete                                  = false
provider count                                 = 7
```

## Next step

Continue only with non-REP custom copy/init code and deeper or indirect alias paths that carry an exact selected-HDVehicle-derived destination. Do not promote a slot from numeric offset overlap, callgraph proximity, or copy opcode alone.
