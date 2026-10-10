# Process 1B — `CreateFiber` callback surface

The pinned PC retail 1.02 SQLite call inventory contains exactly one direct `CreateFiber` call:

```text
FUN_00a62940 @ 0x00a62a43
```

The matching hash-pinned Ghidra C export fixes the fiber start routine at that callsite:

```c
CreateFiber(*(SIZE_T *)(*piVar4 + 8), lpStartAddress_00a62710, piVar4 + 2);
```

`lpStartAddress_00a62710 @ 0x00a62710` is not one of the canonical 15 P1B exact `HDVehicle+0x4330` carrier functions. Therefore this registration surface provides no direct runtime entry into an exact carrier.

The fiber entry subsequently executes object/vtable dispatch through its parameter record; that downstream dispatch is intentionally not claimed by this registration-only proof.

## Reproduce

```bash
python3 tools/ghidra/analyze_p1b_hdvehicle_4330_createfiber_callback_surface.py \
  /path/to/shift_ghidra.sqlite \
  /path/to/SHIFT.exe.c \
  --output evidence/p1b_hdvehicle_4330_createfiber_callback_surface.json
```

The analyzer fails closed on input hash drift, callsite-count drift, an indirect `CreateFiber` row, source-fragment drift, or if the fixed start routine ever enters the canonical P1B carrier set.

## Gate

```text
CreateFiber callback surface complete = true
physical CreateFiber callsites = 1
possible fiber start entrypoints = 1
exact HDVehicle+0x4330 carrier starts = 0

runtime callback registration ruled out = false
indirect entry into carriers ruled out = false
generic function-pointer stores/copies ruled out = false
computed/encoded code pointers ruled out = false
manager+0x374 identity join complete = false
final 0x004b86cf rejection = false
P1.3 complete = false
provider count = 7
```
