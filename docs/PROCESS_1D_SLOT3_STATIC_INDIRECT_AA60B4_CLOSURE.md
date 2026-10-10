# Process 1D — static indirect `0xaa60b4` closure

This P1.3D slice resolves the two non-immediate callsites left open by the direct-callee bulk-opcode inventory in `FUN_00770e80`.

## Static image target

Both callsites use the same machine encoding:

```text
0x00770ec4  ff 15 b4 60 aa 00   call DWORD PTR ds:0xaa60b4
0x00770f41  ff 15 b4 60 aa 00   call DWORD PTR ds:0xaa60b4
```

In the pinned PC retail 1.02 image, `0xaa60b4` is inside `.rdata` and contains the dword `0x00778052`. Thus this bounded image surface is not an unknown target: both calls enter `0x00778052`, an interior entry of `FUN_00777fe0`.

The read-only claim is limited to the PE image section. Arbitrary runtime patching is not globally ruled out.

## Exact-root chain

Merged P1D machine contracts establish `ESI=HDVehicle` throughout the relevant `FUN_00770e80` interval.

At the interior target:

```text
0x00778056  ECX = ESI
0x0077805b  call FUN_0063f350
0x0077806c  ESI = -1
```

Before the clobber, the exact root is not pushed or stored; it is forwarded only as the receiver of `FUN_0063f350`.

`FUN_0063f350` copies receiver `ECX` into `ESI`, reads fields from that object, and forwards the exact receiver once:

```text
0x0063f37b  ECX = ESI
0x0063f37d  call FUN_0063f300
```

On the success path `ESI` is then overwritten at `0x0063f382`; failure paths reach the epilogue without persisting or forwarding the exact root. `FUN_0063f300` likewise reads fields from its exact receiver and overwrites `ESI` with an output argument at `0x0063f329` before any later `ESI` push/copy activity.

No selected wheel-root materialization and no exact-root persistent store are present in this bounded chain.

## Reproduce

```bash
python3 tools/ghidra/analyze_p1d_slot3_static_indirect_aa60b4_pe.py \
  /path/to/SHIFT.exe \
  --output out/p1d_slot3_static_indirect_aa60b4_closure.json
```

The analyzer SHA-locks the two call encodings, the `.rdata` slot, the interior target fragment, `FUN_0063f350`, and `FUN_0063f300`, and also pins all `ESI`-touching instruction addresses in the two callees.

## Boundary

This closes only the two `FUN_00770e80` calls through static image slot `0xaa60b4`. It does not rule out other indirect calls, callback registration, runtime code/data patching, reconstructed pointers, deeper runtime-generated aliases, or hand-unrolled pointer copies.

Therefore global indirect-entry, callee-created-alias, runtime-pointer-storage, stored/escaped-alias, writer-provenance, P1.3D and aggregate P1.3 gates remain false. External provider count remains 7.
