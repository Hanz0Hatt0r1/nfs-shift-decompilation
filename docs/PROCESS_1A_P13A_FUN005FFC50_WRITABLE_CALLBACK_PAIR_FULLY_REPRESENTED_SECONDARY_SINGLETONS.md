# Process 1A / P1.3A — fully represented secondary singleton values

## Scope

The secondary-operand inventory leaves 27 two-GPR single-TOP sites where the non-TOP operand is represented in every original may-state observation. This pass checks whether that represented operand is itself ambiguous.

## Retail result

On PC retail 1.02 `SHIFT.exe` (SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`):

- 27 static sites / 32 observations
- non-singleton secondary observations: 0
- secondary value `0x00aa9b60`: 21 sites / 23 observations
- secondary value `0x00000000`: 6 sites / 9 observations
- instruction classes: CMP 19, MOV 5, LEA 3
- TOP primary registers: EAX 18, EDI 4, ESI 3, EBX 2
- secondary registers: ECX 13, EDX 5, EBP 4, EBX 3, ESI 2

Every secondary operand in this 27-site class is therefore an exact singleton. It can be folded into the affine expression without introducing a new widening dimension.

## Gate effect

Promoted only:

- `p13a_fun005ffc50_writable_callback_pair_fully_represented_secondary_singleton_subset_complete`
- `writable_callback_pair_fully_represented_secondary_values_all_singleton`

The 27-site frontier is not declared closed because the primary operand remains widened. All broader alias/runtime/callback/slot/P1.3 gates remain fail-closed and external provider count remains 7.

## Next

Fold the singleton secondary into each affine expression and classify the remaining widened primary operand with the congruence/provenance domain.
