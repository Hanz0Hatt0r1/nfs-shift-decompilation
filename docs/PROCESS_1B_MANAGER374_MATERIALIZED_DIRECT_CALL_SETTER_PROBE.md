# Process 1B — materialized `manager+0x374` direct-call setter probe

## Blocker

The literal `+0x374` writer surface is closed 25/25 and the bounded same-region / EBP / normalized-ESP materialized-address probes produced a zero retail candidate frontier. The remaining helper-mediated setter class still includes a distinct transport that those probes intentionally stop before: code can materialize `receiver+0x374`, pass that exact target address to a helper, and the helper can write through the argument as `[arg]` without carrying literal `+0x374` in its own instruction.

This probe covers that one-hop direct-call transport. It does not claim global helper/non-vtable setter closure.

## Tool

```text
tools/ghidra/analyze_p1b_manager374_materialized_direct_call_setters.py
```

Output format:

```text
SHIFT.P1B.Manager374MaterializedDirectCallSetterProbe/1
```

Authority is SHA-locked PC retail 1.02 `SHIFT.exe`:

```text
eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1
```

## Bounded transport

The caller side accepts only:

1. exact `lea addr,[receiver+0x374]`;
2. exact GPR `mov` copies of that address;
3. forwarding at the first call through:
   - `ECX`;
   - `EDX`;
   - pushed stack arguments.

A call with a non-direct target is recorded as an unresolved indirect boundary and is never followed speculatively.

For a direct target found in the retail disassembly, the callee is scanned for at most 96 instructions. Entry aliases are seeded from `ECX`/`EDX` and logical stack-argument offsets. The callee model supports:

- GPR alias copies;
- stack-argument reloads from `ESP` or an `EBP` frame;
- `push` / `pop` stack movement;
- immediate `add/sub esp,imm`;
- exact `lea esp,[esp+/-imm]`;
- `mov ebp,esp` frame establishment.

A candidate is emitted only for an exact zero-displacement dereference through the recovered alias with an explicit memory-write/RMW mnemonic. Read-only forms such as `cmp [alias],...`, `test [alias],...` and `push [alias]` do not count as writes.

## Fail-closed boundaries

The callee scan stops on:

- a nested call;
- branch/jump/return/trap control flow;
- dynamic or unsupported stack-pointer mutation;
- the 96-instruction bound.

The caller clears target-address provenance after a call/control boundary. Mutating the tracked materialized address, for example `add eax,4`, invalidates it before argument forwarding.

The probe deliberately does not cover:

- indirect callees;
- helper-returned target addresses;
- nested helper chains;
- CFG joins/cross-block alias carry;
- non-stack memory persistence of the materialized address;
- runtime patching/generated code;
- external process mutation.

## Gate policy

A successful scan may set only:

```text
materialized_plus_374_direct_call_argument_subset_scanned = true
```

It must not promote these without additional authoritative evidence and candidate adjudication:

```text
materialized_plus_374_direct_callee_write_through_candidates_classified
materialized_helper_mediated_setter_surface_complete
helper_returned_materialized_address_surface_complete
global_helper_non_vtable_indirect_setter_surface_complete
external_or_unknown_origin_outer_alias_surface_complete
global_manager_root_origin_surface_complete
manager_374_join_to_hdvehicle_4330_complete
last_literal_0x004b86cf_rejected
p1_3_control_producer_complete
```

External provider count remains `7`.

## Tests

```bash
python3 -m pytest -q \
  tests/test_process1b_manager374_materialized_direct_call_setters.py
```

Regressions cover register arguments, stack arguments across a conventional EBP frame, argument spacing, read-only memory operands, tracked-address mutation, nested calls, indirect calls, dynamic ESP adjustment, direct-target parsing and fail-closed semantic gates.

## Next step

Run the probe on the authoritative retail image. If the direct-callee write-through frontier is empty, this one-hop helper-mediated transport class can be closed separately. Positive candidates must be classified by receiver provenance and value domain before any broader helper/non-vtable setter gate changes. The remaining helper-returned-address and indirect-call classes stay open until independently bounded.
