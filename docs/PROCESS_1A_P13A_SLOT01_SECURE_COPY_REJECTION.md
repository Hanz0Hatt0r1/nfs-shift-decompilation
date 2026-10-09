# Process 1A / P1.3A — nearest secure-copy branch rejection

## Blocker

After the named-memory frontier was pinned, the first game-side copy candidates for slot0 `HDVehicle+0x938` and slot1 `HDVehicle+0x13b8` were the `_memcpy_s` / `_memmove_s` paths under `FUN_0070fae0` and `FUN_00647820`.

These paths are now rejected by direct PC-retail machine transfer rather than by callgraph distance or symbol names.

## String backing-store proof

The exact retail bytes show a common string-storage family:

- `FUN_006310d0` allocates storage, advances the returned pointer by six bytes for the payload, and stores that pointer in `[this]`.
- `FUN_00631230` obtains the secure-move destination with `mov ecx,[edi]` at `0x00631247`, then invokes `0x00906fb6` (`_memmove_s`) at `0x0063124d`. The target of the copy is therefore the separately allocated backing buffer, not the inline string object.
- `FUN_00631740` allocates a backing buffer through `FUN_006310d0`, obtains the copy destination with `mov eax,[ebx]` at `0x00631796`, then invokes `0x00900dea` (`_memcpy_s`) at `0x0063179c`.
- `FUN_006329e0` performs a bounded NUL-length scan and funnels all non-null paths through `FUN_00631230`.

The verifier `tools/ghidra/analyze_p1a_slot01_secure_copy_machine.py` validates the retail executable hash plus the exact byte windows and rel32 call targets.

## Nearest branch receivers

`FUN_0070fae0` invokes the string assignment wrapper on explicit subobjects:

```text
object+0x370
object+0x374
object+0x378
object+0x37c
object+0x380
```

The remaining path creates a stack-local string object whose source is `object+0x380`. The secure-copy destination still resolves through that string object's separately allocated `[this]` buffer.

`FUN_00647820` similarly calls the same assignment wrapper with receiver `containing_object+0x24`.

Therefore the named secure copies selected by the previous frontier do not write inline bytes at wheel-local `+0x538`, slot0 `HDVehicle+0x938`, or slot1 `HDVehicle+0x13b8`.

## Gate

```text
nearest named secure-copy branches rejected = true
all named copy paths exhausted               = false
inline/custom bulk copy ruled out            = false
indirect copy dispatch ruled out              = false
slot0 alias/callee/bulk-copy complete         = false
slot1 alias/callee/bulk-copy complete         = false
P1.3 complete                                 = false
provider count                                = 7
```

## Next step

Remove these secure-string paths from the candidate set. Continue with interprocedural aliases and inline/custom copy or initialization ranges, requiring exact selected-HDVehicle root provenance and exact target-byte coverage before any slot gate is promoted.
