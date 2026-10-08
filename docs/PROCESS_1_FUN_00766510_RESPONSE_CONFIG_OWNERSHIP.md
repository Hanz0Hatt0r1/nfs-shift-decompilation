# Process 1 — `FUN_00766510` response-configuration ownership

## BLOCKER

P1.1 requires the remaining `FUN_00766510` response configuration to have a PC-retail owner before Process 2 can remove the top-level `contact_response` provider. This slice closes the owner/write surface for `HDVehicle+0x3908`, `+0x3910`, `+0x3918`, and the six-vector table beginning at `+0x3950`.

## INPUT

Authoritative input is the PC retail 1.02 Ghidra export `SHIFT.exe.c` with SHA-256 `512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9`. The retail executable identity remains MD5 `705af8b420e5eb1e3834ac43d5533c6b`, SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`.

Xbox 360 recompilation was available on Drive but is not required for any promoted claim in this slice.

## OUTPUT

`SHIFT.Fun00766510ResponseConfigOwnership/1` proves:

- `HDVehicle+0x3910` has one setup assignment in `FUN_00756bb0`, copied from `setup_param_2+0x730`;
- `HDVehicle+0x3918` is configured once in `FUN_00756bb0` by `FUN_00752f10` from `setup_param_2+0x738/+0x740/+0x748` and is consumed by `FUN_00755340` in `FUN_00766510`;
- `HDVehicle+0x3950..+0x39d8` is a six-entry, `0x18`-byte vector table. `FUN_0076b130` constructs six entries and `FUN_00756bb0` populates them from six setup records starting at `setup_param_2+0x750` with a `0x48`-byte source stride, after `FUN_007a6be0` evaluation;
- `HDVehicle+0x3908` has one direct store site, inside `FUN_00756ac0`, with the recovered formula `(+0x3750*s*s) + (+0x3748*s) + (+0x3740)`.

The important negative result is that `+0x3908` is **not** immutable setup data. Setup seeds it once, but `FUN_00757e60`, `FUN_00758210`, and `FUN_00769d60` recompute it from persistent selector state `+0x3c78` after mutating/resetting its coefficient state. A native consumer must therefore preserve `+0x3908` as persistent derived state plus mutation hooks; treating it as a selected BMW constant would be wrong.

## CONSUMER

Process 2 may use this contract to remove per-pass authority over `+0x3910/+0x3918/+0x3950` and to model `+0x3908` as persistent derived state. This slice does not itself edit native runtime code.

## GATES_CHANGED

- response-config owner/write provenance: **closed**;
- `+0x3910/+0x3918/+0x3950` per-pass provider requirement: **false**;
- `+0x3908` setup-constant claim: **false**;
- complete `FUN_00766510/contact_response` internalization: **still false**;
- active external-provider count: unchanged at **7**.

## LIMITS

This proof does not yet provide all selected BMW numeric values for these structures. It also does not close the earlier `+0x3b20` branch, optional `+0x3bc8/+0x3cxx` branch, or every auxiliary/state/diagnostic write in `FUN_00766510`.

## TESTS

`tests/test_process1_fun_00766510_response_config_ownership.py` pins the evidence contract, PC source hash, owner classification, recovered source offsets, non-constant `+0x3908` conclusion, and the analyzer anchors.

## NEXT_OWNER

Process 2 can consume the positive owner contract. Process 1 remains owner of the rest of P1.1.

## NEXT_STEP

Process 1 should next close the earlier `+0x3b20` response branch and then the optional `+0x3bc8/+0x3cxx` branch, including the source-visible state/diagnostic writes required before `contact_response` can be removed.
