# Process 1B — helper-returned materialized `+0x374` target probe

## Playable-slice blocker

The decoded-image `manager+0x374` writer investigation has separate closures for literal destinations, computed forwarding, direct exact-root writers, exact-getter aliases, Participants lifecycle helper/indirect setters, same-region materialized addresses, stack spill/reload carriers, and one-hop direct helpers that receive an already-materialized target address.

A different helper-mediated transport remains open: a helper can receive a receiver object, return `receiver+0x374` in `EAX`, and let its caller write through that returned address. In that pattern neither the caller's write nor the helper's return needs to carry a literal `+0x374` destination.

This probe bounds that specific direct-helper / immediate post-return class. It does not claim global helper or runtime-origin closure.

## Tool and contract

```text
tools/ghidra/analyze_p1b_manager374_helper_returned_materialized_targets.py
SHIFT.P1B.Manager374HelperReturnedMaterializedTargetProbe/1
```

The executable is SHA-locked to PC retail 1.02:

```text
eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1
```

## Helper qualification

For every local direct CALL target, the helper is scanned for at most 96 instructions. At entry the exact symbolic base channels are:

```text
ECX
EDX
positive stack arguments
```

The bounded model carries an exact `(argument_channel, delta)` pair through:

- `mov reg,reg`;
- `lea reg,[tracked_reg+/-imm]`;
- `add/sub tracked_reg,imm`;
- stack-argument loads from normalized `ESP` or `EBP` frames.

Stack coordinates support:

- `push` / `pop`;
- immediate `add/sub esp,imm`;
- exact `lea esp,[esp+/-imm]`;
- `mov ebp,esp`;
- standard `mov esp,ebp` / `leave` epilogues.

A helper qualifies only when its bounded return leaves:

```text
EAX = one exact entry argument + 0x374
```

A constant that merely ends in hexadecimal `374` does not qualify.

## Fail-closed helper boundaries

The helper is rejected for this subset when it encounters:

- a nested call;
- a branch/jump/trap before the return;
- a dynamic or unsupported stack adjustment;
- an unsupported mutation that destroys tracked provenance;
- the 96-instruction bound without a qualifying return.

Partial-register writes kill the parent GPR provenance. Selected implicit x86 clobbers (`mul/div`, `cdq`, `cpuid`, `xchg/xadd`, string/REP forms, and related accumulator mutations) are also invalidated conservatively.

This is intentionally a straight-line return proof; no CFG merge is inferred.

## Caller post-return scan

Each direct callsite of a qualifying helper seeds:

```text
EAX = exact helper-returned target address
```

For at most 32 following instructions, the probe tracks only exact GPR `mov` copies. It emits a write candidate only when an explicit write/RMW mnemonic dereferences the exact returned alias at zero displacement:

```text
mov [eax],...
mov [edi],...     # after mov edi,eax
add [eax],...
...
```

Read-only forms such as:

```text
cmp [eax],...
test [eax],...
push [eax]
```

are not write candidates.

The post-return scan stops at the next call, branch/jump, return/trap, or after 32 instructions. Arithmetic mutation such as `add eax,4` destroys exact-target provenance.

## Explicitly outside scope

This probe does not cover:

- indirect call targets;
- imported/external helpers whose bodies are not in the retail image;
- helpers whose return requires CFG joins or nested calls;
- stack or non-stack memory persistence of the returned target in the caller;
- target addresses synthesized from unrelated opaque inputs rather than a recognized entry argument;
- runtime patching or generated/self-modifying code;
- arbitrary external process mutation.

Those remain separate fail-closed classes.

## Gate policy

A successful analyzer run sets only the bounded acquisition gate:

```text
direct_helper_returned_plus_374_target_subset_scanned = true
```

It does not promote these without an authoritative retail run and classification of every positive write candidate:

```text
helper_returned_plus_374_write_candidates_classified
helper_returned_materialized_address_surface_complete
global_helper_non_vtable_indirect_setter_surface_complete
external_or_unknown_origin_outer_alias_surface_complete
independent_unnamed_opaque_or_external_runtime_root_synthesis_complete
unrecognized_runtime_transform_root_origin_surface_complete
global_manager_root_origin_surface_complete
manager_374_join_to_hdvehicle_4330_complete
last_literal_0x004b86cf_rejected
p1_3_control_producer_complete
```

External provider count remains `7`.

## Regression coverage

```bash
python3 -m pytest -q \
  tests/test_process1b_manager374_helper_returned_materialized_targets.py
```

Tests cover:

- `ECX+0x374` return followed by direct write;
- `EDX` propagation through `mov/add`;
- stack argument through a standard EBP frame and `leave`;
- post-return GPR copy;
- branch and nested-call rejection;
- post-return arithmetic clobber;
- read-only dereference separation;
- unrelated constant returns;
- indirect and external call exclusion;
- dynamic stack adjustment;
- partial-register clobber;
- GNU objdump direct-target forms;
- fail-closed final gates.

## Next step

Run the probe on the authoritative PC retail 1.02 image. If the post-return write frontier is empty, close only this direct-local-helper / immediate-caller subset. If positive candidates exist, classify each callsite's helper argument receiver provenance and written value domain before any broader helper/non-vtable setter claim. Indirect/external helpers and persisted returned-target carriers remain separate until independently bounded.
