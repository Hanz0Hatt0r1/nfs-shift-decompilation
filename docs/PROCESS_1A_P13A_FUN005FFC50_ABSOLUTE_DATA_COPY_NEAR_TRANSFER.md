# Process 1A / P1.3A — absolute `.data` load copied across GPRs before transfer

## Scope

`SHIFT.P1A.P13AFun005ffc50AbsoluteDataLoadNearTransfer/1` closes the same-register shape: an absolute writable `.data` dword is loaded into one GPR and that same GPR is used by a nearby `call/jmp`. It explicitly leaves register copies open.

This contract keeps the same 16-decoded-instruction straight-line window, but preserves pointer identity through `mov dst,src` and `xchg` between 32-bit GPRs. A copied register may survive clobber of the original register. Any other control transfer terminates the window; writes remove only the affected tainted register, and the window ends once no tainted GPR remains.

## Retail result

The upstream inventory remains **1,786** absolute `.data` memory-content loads from **434** unique slots across **2,847,850** decoded instructions.

Only **10** loads produce an identity-preserving GPR copy in the bounded window. All 10 are `mov` copies; pair counts are:

- `EAX -> ECX`: 2;
- `EAX -> EDX`: 1;
- `ECX -> EAX`: 1;
- `ECX -> EDX`: 2;
- `EDI -> EAX`: 1;
- `EDI -> ECX`: 2;
- `EDX -> ECX`: 1.

There are **0** indirect `call/jmp` transfers through any tainted register and therefore **0** transfers through a copied register.

Compared with the same-register #1930 scan, copy propagation moves two windows from the original-register-clobber bucket to the unrelated-control-transfer bucket: termination becomes 1,357 other control transfers, 411 all-tainted-register clobbers, and 18 window expirations. Neither extended path reaches an indirect transfer.

## Boundary

Promoted only `p13a_fun005ffc50_absolute_data_register_copy_near_transfer_subset_complete=true`.

This does **not** cover pointer arithmetic/transforms, stack spill/reload, inter-block carry, base/index-addressed writable memory, aliases, heap/runtime-generated values, or whole-program points-to provenance. Global writable-memory, callback/incoming-indirect, slot0, slot1 and aggregate P1.3 gates remain fail-closed. Provider count remains 7.

## Reproduction

```bash
python tools/ghidra/analyze_p1a_fun005ffc50_absolute_data_copy_near_transfer.py /path/to/SHIFT.exe \
  --upstream evidence/p1a_p13a_fun005ffc50_absolute_data_load_near_transfer.json \
  --output evidence/p1a_p13a_fun005ffc50_absolute_data_copy_near_transfer.json
pytest -q tests/test_process1a_p13a_fun005ffc50_absolute_data_copy_near_transfer.py
```

## Next step

Trace arithmetic/transformed and spill/reload values loaded from writable memory, then base/indexed/alias sources. The absolute-load plus same-block GPR-copy class no longer needs to be rescanned.
