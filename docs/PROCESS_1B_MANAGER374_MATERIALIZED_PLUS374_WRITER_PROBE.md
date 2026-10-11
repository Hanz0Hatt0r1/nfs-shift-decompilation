# Process 1B: materialized `+0x374` writer probe

## Blocker

Merged whole-image direct-displacement coverage inventories write/RMW instructions whose destination itself contains exact `+0x374`, such as `mov [ecx+0x374],eax`.

A separate setter class remains possible when code first materializes the target address and writes through it later:

```text
lea eax,[ecx+0x374]
...
mov [eax],edx
```

That class directly affects the remaining helper/non-vtable setter frontier for the final `manager+0x374 -> HDVehicle+0x4330` identity adjudication.

## Probe

`tools/ghidra/analyze_p1b_manager374_materialized_plus374_writers.py` is SHA-locked to authoritative PC retail 1.02 `SHIFT.exe`.

Within straight-line machine regions it tracks only:

- exact `lea addr,[receiver+0x374]` with one GPR receiver and no index;
- exact GPR `mov` copies of that materialized address;
- exact zero-displacement first-memory-operand dereferences `[addr]`;
- an explicit write/RMW mnemonic allowlist.

Control transfers terminate the state. Full and partial register writes invalidate exact address provenance. Selected x86 implicit clobbers (`cmpxchg`, one-operand multiply/divide, timestamp/CPUID forms, string operations, and stack-pointer mutations) are modeled conservatively to avoid stale-address false positives.

Indexed materializers such as `lea eax,[ecx+edx*4+0x374]` are excluded because they are not exact `receiver+0x374` identity.

## Gate effect

This probe establishes only the bounded same-region materialized-address candidate surface after an authoritative retail run. A recovered receiver register is syntactic provenance, not Participants Manager identity.

These remain fail-closed:

- `materialized_plus_374_candidate_receivers_classified`;
- complete computed `+0x374` writer coverage;
- unknown/unrelated manager-root alias closure;
- global helper/non-vtable setter closure;
- global manager-root origin closure;
- `manager+0x374 -> HDVehicle+0x4330` identity join;
- final `0x004b86cf` / slot2 rejection;
- aggregate P1.3.

Provider count remains 7.

## Limits

The subset does not cover arithmetic reconstruction of the address, stack spill/reload of the materialized pointer, cross-control-flow carry, helper-returned pointers, or memory-stored pointer aliases. Those classes must remain separate and evidence-driven.

## Next

Run on authoritative retail `SHIFT.exe`. Classify only positive materialized `+0x374` write receivers. Extend provenance only for surviving candidates, then compose with the direct-displacement inventory before any final manager identity or slot2 promotion.
