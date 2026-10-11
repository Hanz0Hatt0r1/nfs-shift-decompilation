# Process 1A / P1.3A — modulus-1 local induction bounds

## Scope

This subset refines the seven `0 mod 1` sites isolated by `SHIFT.P1A.P13AFun005ffc50WritableCallbackPairTargetCompatibleCongruenceFrontier/1`. Congruence alone has no exclusion power at these sites, so this pass uses only explicit local induction structure visible in PC retail 1.02 `SHIFT.exe`.

## Retail proof

Four sites have exact bounded primary counters while the secondary operand is the upstream singleton `0x00aa9b60`:

- `0x004b9124`: `EAX=0` at the memory use. `xor eax,eax` enters the loop; the back-edge first increments EAX to 1 and `cmp eax,1; jb 0x4b9124` cannot return.
- `0x006084d0`: `EDI` starts at 0 and the loop body is guarded by `cmp edi,0xff; jae 0x6084db`, so the use sees `EDI=0..254`.
- `0x00608539` and `0x0060853f`: after the same loop, `EDI=0..255`.

The resulting effective-address ranges are `0x00aa9b60..0x00aa9c60`, far below callback slots `0x00b87b7c/80`. All four sites are therefore impossible callback-slot aliases.

The remaining modulus-1 sites are `0x00503328`, `0x0050334b`, and `0x005d5621`; their primary `ESI` provenance is not closed here.

## Boundary

This is not a global range analysis. It recognizes only the exact retail instruction patterns asserted by the analyzer. The eight compatible modulo-4/8 sites, the three unresolved modulus-1 sites, the 1,095 missing-secondary sites, runtime mutation, stack/heap aliases, and aggregate P1.3 gates remain fail-closed.

## Reproduction

```bash
python tools/ghidra/analyze_p1a_fun005ffc50_writable_callback_pair_mod1_local_induction_bounds.py \
  SHIFT.exe \
  --upstream evidence/p1a_p13a_fun005ffc50_writable_callback_pair_target_compatible_congruence_frontier.json \
  --output /tmp/mod1_bounds.json
pytest -q tests/test_process1a_p13a_fun005ffc50_writable_callback_pair_mod1_local_induction_bounds.py
```

Next: trace producer/join provenance for ESI at the three remaining modulus-1 sites.
