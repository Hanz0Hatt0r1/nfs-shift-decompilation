# Process 1D — corrected `0xaa60b4` import-indirect closure

## Correction

`SHIFT.P1D.Slot3StaticIndirectAA60B4Closure/2` supersedes `/1`.

The original contract correctly pinned the two `FUN_00770e80` machine callsites but incorrectly interpreted the **on-disk** dword stored at `0x00aa60b4` (`0x00778052`) as a code virtual address. In this PE image that dword is an `IMAGE_IMPORT_BY_NAME` RVA used by the import lookup/IAT before loader fixup. It must not be disassembled as an interior entry of `FUN_00777fe0`.

The corrected proof resolves the slot through the PE import descriptors.

## PE import resolution

Both callsites have the same encoding:

```text
0x00770ec4  ff 15 b4 60 aa 00   call DWORD PTR ds:0xaa60b4
0x00770f41  ff 15 b4 60 aa 00   call DWORD PTR ds:0xaa60b4
```

The exact PE32 import metadata is:

```text
image base                    = 0x00400000
IAT slot VA                   = 0x00aa60b4
IAT slot RVA                  = 0x006a60b4
import descriptor RVA         = 0x007776bc
DLL                           = KERNEL32.dll
OriginalFirstThunk RVA        = 0x00777938
FirstThunk RVA                = 0x006a6088
thunk index                   = 11
IMAGE_IMPORT_BY_NAME RVA      = 0x00778052
hint                          = 0x0229
name                          = InterlockedExchange
on-disk FirstThunk value      = 0x00778052
```

At RVA `0x00778052`, the image contains the import hint followed by the ASCII name `InterlockedExchange`. At runtime the Windows loader replaces the IAT entry with the resolved address of `KERNEL32!InterlockedExchange`.

Therefore the two `call [0xaa60b4]` instructions are import calls, not jumps into the game's `.text` section.

## Exact call semantics

The first bounded caller window is:

```text
0x00770ebb  push 1
0x00770ebd  lea  eax,[esi+0x4020]
0x00770ec3  push eax
0x00770ec4  call DWORD PTR ds:0xaa60b4
```

With merged `ESI=HDVehicle`, this is:

```text
InterlockedExchange((LONG volatile*)(HDVehicle+0x4020), 1)
```

The second bounded call likewise pushes `2`, materializes `HDVehicle+0x4020`, and invokes the same IAT slot:

```text
InterlockedExchange((LONG volatile*)(HDVehicle+0x4020), 2)
```

These are scalar atomic state writes. They do not pass, persist, reconstruct, or materialize a selected wheel pointer.

## Reproduce

```bash
python3 tools/ghidra/analyze_p1d_slot3_static_indirect_aa60b4_pe.py \
  /path/to/SHIFT.exe \
  --output evidence/p1d_slot3_static_indirect_aa60b4_closure.json
```

The analyzer validates the retail executable SHA-256, parses the PE import directory, resolves the exact descriptor/thunk/import-name tuple, checks both call encodings, and hash-locks the caller argument-setup windows.

## Gate

```text
FUN_00770e80 aa60b4 import-indirect subset complete = true
runtime target unknown                               = false
runtime target                                       = KERNEL32!InterlockedExchange
on-disk 0x00778052 treated as code VA               = false
selected wheel alias found                           = false
exact HDVehicle-root persistent store found          = false
scalar state target                                  = HDVehicle+0x4020

other indirect entry ruled out                       = false
callee-created aliases ruled out                     = false
runtime-generated pointer stores ruled out           = false
stored-or-escaped aliases ruled out                  = false
slot3 writer provenance proven                       = false
P1.3D complete                                       = false
aggregate P1.3 complete                              = false
provider count                                       = 7
```

## Boundary

This correction closes only the two `FUN_00770e80` calls through IAT slot `0x00aa60b4`. Other indirect calls, callbacks, reconstructed pointers, runtime-generated/copied aliases, and hand-unrolled pointer-copy patterns remain open.

The semantic owner remains **Process 1D / P1.3D**. This update corrects the canonical machine interpretation; it does not transfer ownership to Process 1A.
