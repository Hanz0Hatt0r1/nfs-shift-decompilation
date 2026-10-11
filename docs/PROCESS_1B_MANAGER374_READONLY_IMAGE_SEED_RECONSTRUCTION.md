# Process 1B — read-only image-seeded manager-root reconstruction probe

## Blocker

`SHIFT.P1B.Manager374RuntimeRootFrontier/2` still leaves memory-load/opaque runtime reconstruction outside the canonical exact-root lineage. Existing Process 1B contracts already close:

- direct literal singleton references;
- same-register immediate arithmetic;
- constant-only multi-register synthesis;
- static exact-pointer cells;
- known canonical-lineage return/copy/derived-subobject paths;
- the three retail materialized `receiver+0x374` transport classes.

A narrower unresolved static class remains: a function can load a non-root dword from immutable image bytes and then reconstruct `0x00bc9fc0` arithmetically without containing that value as an immediate literal.

## Probe

`tools/ghidra/analyze_p1b_manager374_readonly_image_seed_reconstruction.py` is SHA-locked to authoritative PC retail 1.02 `SHIFT.exe`:

```text
eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1
```

Only dword loads from PE `.text` and `.rdata` are accepted as seeds. `.data`, heap, anonymous memory and unresolved memory operands are deliberately excluded because their runtime values are not immutable static evidence.

For each seed the analyzer carries exact 32-bit values for at most **32 decoded instructions** in the same straight-line region. Modeled operations are:

- full-GPR `mov` copies;
- `add/sub/xor/or/and` with an immediate or another exact tracked GPR;
- `inc/dec/neg/not`;
- `shl/sal/shr` with an immediate count;
- single-base `lea reg,[tracked_reg+/-imm]`;
- three-operand `imul dst,tracked_reg,imm`.

Calls, jumps, conditional branches, loops, returns, traps and system transitions clear all state. Unsupported writes to a tracked register destroy that register's provenance. `xor reg,reg` deliberately removes memory-seed lineage because the result no longer depends on the seed.

Every exact formation of Participants Manager root `0x00bc9fc0` is emitted with all contributing read-only image seed sites/addresses.

## Output contract

```text
SHIFT.P1B.Manager374ReadonlyImageSeedReconstruction/1
```

Important surface fields:

- `readonly_image_seed_load_count`
- `modeled_transition_count`
- `exact_root_formation_count`
- `direct_exact_root_seed_count`
- `nontrivial_exact_root_reconstruction_count`
- `nontrivial_exact_root_reconstructions`
- window/control/clobber counters.

A direct read-only cell containing the root is reported separately from a nontrivial reconstruction. The older static exact-pointer-cell contract expects no such unrelated cell, but this probe independently checks the selected load grammar when run on retail.

## Reproduction

```bash
python3 tools/ghidra/analyze_p1b_manager374_readonly_image_seed_reconstruction.py \
  /path/to/SHIFT.exe \
  --output /tmp/p1b-manager374-readonly-seed-reconstruction.json
```

Focused regressions:

```bash
python3 -m pytest -q \
  tests/test_process1b_manager374_readonly_image_seed_reconstruction.py
```

## Proof boundary

This promotes only:

```text
bounded_readonly_image_memory_seed_reconstruction_subset_complete=true
```

It does **not** promote any of:

```text
memory_load_or_opaque_runtime_reconstruction_complete
independent_unnamed_opaque_or_external_runtime_root_synthesis_complete
unrecognized_runtime_transform_root_origin_surface_complete
global_manager_root_origin_surface_complete
manager_374_join_to_hdvehicle_4330_complete
last_literal_0x004b86cf_rejected
p1_3_control_producer_complete
```

External provider count remains **7**.

Still outside this probe are writable/runtime memory loads, indexed/table-derived loads, helper-return values, inter-block/CFG carry, arbitrary memory aliases, runtime patching/self-modifying code, encoded values that require unsupported transforms, and external process mutation.

## Next step

Run the probe on authoritative retail and classify any positive exact-root formation. If the result is negative, compose it as one additional bounded negative source class and continue with writable-memory/helper-return and unrecognized-runtime-transform acquisition. Do not infer global manager-root origin closure from this subset alone.
