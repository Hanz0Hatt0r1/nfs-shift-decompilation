# Process 1A — reject `0x00991650` from the participant `+0x4b0` frontier

## BLOCKER

After the `FUN_00481e20` bulk-copy rejection, nine direct-displacement `+0x4b0` candidates remained. `0x00991650` is one of them.

## OUTPUT

The candidate is not root-relative PhysicsParticipant state. `FUN_00991540` first computes an indexed record:

```text
iVar4 = param_2 * 0x124 + in_EAX[1]
...
*(uint *)(iVar4 + 0x4b0) = local_c
```

Retail machine transfer matches this geometry: the destination base is `[decoder_state+4] + index*0x124`, then the literal `+0x4b0` displacement is applied.

The parser chain is exact:

```text
FUN_00963383
  -> [codec+0x108]
  -> FUN_00991e60
  -> FUN_00991b00
  -> FUN_009918c0
  -> FUN_00991540
```

The same codec lifecycle is rooted by `FUN_00963478`: it checks the `fLaC` magic, stores `FUN_0098f9d0()` at `codec+0x108`, and allocates codec state through the literal source path `..\..\src\fmod_codec_flac.cpp`.

Therefore the `0x00991650` store is FMOD FLAC decoder record state, not selected `0x2b90` PhysicsParticipant `+0x4b0`.

## GATES_CHANGED

- `0x00991650`: **rejected**;
- FLAC decoder record owner/domain: **closed**;
- unresolved direct-displacement candidates: **8**;
- selected participant runtime `+0x4b0` producer: **open**;
- P1.1a/P1.1: **incomplete**;
- `contact_response` removal: **not authorized**;
- provider count: **7**.

## NEXT_STEP

Continue exact receiver-provenance adjudication of the remaining eight direct-displacement candidates before widening to computed-address, escaped-alias, indirect-dispatch, or residual bulk-copy paths.
