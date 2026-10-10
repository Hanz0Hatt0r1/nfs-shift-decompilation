# Process 1A / P1.3A — resolve `0x006022ee` slot-4 candidate as CommUDP

## Scope

`SHIFT.P1A.P13AFun0067b660Slot4DispatchAbiFrontier/1` found exactly two bounded one-argument, caller-cleaned slot-`+0x4` register-call shapes: `0x006022ee` and `0x006145c4`. The second is the registry path. This contract resolves the first candidate on its complete direct/static entry surface.

## Network object and wrapper provenance

The containing network object installs vptr `0x00adccb8`; table slot `+0x20` is `FUN_005c4a90`. This is distinct from the animation vtable `0x00af7544` that owns `FUN_0067b660` at slot `+0x4`.

`FUN_005c4a90` drives two wrapper records at object `+0x1c` and `+0x54`. The backing network fields are constructed by `FUN_00601960`:

- return at `0x005bfdad` -> object `+0x20`;
- return at `0x005bfdf2` -> object `+0x24`;
- return at `0x005bff3f` -> object `+0x58`.

The two direct calls to wrapper constructor `FUN_006021a0` consume only those record fields. `FUN_006021a0` stores its first pointer argument into wrapper offset `+0x0` at `0x00602211`.

The whole retail image has exactly three direct calls to `FUN_006022d0`. Two consume object wrappers `+0x1c/+0x54` directly; the third is inside `FUN_005bcc00`, whose only two direct callers are the same `+0x54/+0x1c` records. There are zero exact raw absolute-VA or RVA literals for `FUN_006022d0`.

## Exact indirect targets

`FUN_00601960` builds the function table in the returned object itself:

```text
0x006019f0  [object+0x04] = 0x00600f60
0x00601a21  [object+0x20] = 0x00601030
```

`FUN_006022d0` later reloads wrapper `+0x0` and performs:

```text
0x006022da  EAX = [object+0x20]
0x006022dd  call EAX
...
0x006022ea  ECX = [object+0x04]
0x006022ed  push object
0x006022ee  call ECX
```

Therefore on the complete direct/static wrapper provenance proved here:

- `0x006022dd -> FUN_00601030`;
- `0x006022ee -> FUN_00600f60`;
- `0x006022ee` is **not** `FUN_0067b660`.

## Gate effect

Promoted only the bounded direct/static candidate-resolution gates. Reconstructed, encoded, or runtime-generated entry to `FUN_006022d0` remains open, so global callback/incoming-indirect closure is not promoted. The independent `0x006145c4` dynamic-registry candidate remains open. Slot0, slot1, aggregate P1.3, runtime-generated selected-wheel-store negative, and stored-alias gates remain fail-closed. Provider count remains 7.

## Reproduction

```bash
python tools/ghidra/analyze_p1a_slot4_candidate_6022ee_commudp.py /path/to/SHIFT.exe \
  --upstream evidence/p1a_p13a_fun0067b660_slot4_dispatch_abi_frontier.json \
  --output evidence/p1a_p13a_slot4_candidate_6022ee_commudp_resolution.json
pytest -q tests/test_process1a_p13a_slot4_candidate_6022ee_commudp.py
```

## Next step

Continue the remaining `0x006145c4` dynamic registry candidate and reconstructed/indirect incoming-entry classes. The direct/static `0x006022ee` path should no longer be treated as an animation slot-4 candidate.
