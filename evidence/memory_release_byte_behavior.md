# SHIFT release-byte behavior evidence

`tools/ghidra/analyze_release_byte_behavior.py` tracks whether the release-path
entry `DL` byte influences observable instructions in the retail release thunk
and backend.

Output format:

```text
SHIFT-MEMORY-RELEASE-BYTE-BEHAVIOR/1
```

## Scope

The analyzer consumes the targeted backend instruction export and studies only:

- `0x0064f4c0` / `thunk_FUN_0064f3a0`;
- `FUN_0064f3a0`.

Entry `DL` is taint-tracked through a small fail-closed x86 subset. The report
records:

- whether the thunk forwards `DL` to `FUN_0064f3a0`;
- whether backend instructions read a value influenced by entry `DL`;
- `TEST` / `CMP` observations influenced by the byte;
- conditional branches whose flags depend on the byte;
- bitwise transformations such as `AND`, `OR`, shifts or XOR;
- outgoing transfers carrying tainted `DL`/`EDX`/related register values;
- unsupported tainted writes as explicit uncertainty.

## Deliberate semantic boundary

This is behavior evidence only. Even if retail instructions mask `DL` and branch
on the result, that does not by itself identify the byte as:

- a release flag;
- delete/destructor kind;
- ownership state;
- `operator delete` selector.

Accordingly these remain false:

```text
release_flag_role_proven
delete_kind_role_proven
destructor_policy_proven
operator_delete_identity_proven
ownership_semantics_proven
```

A later semantic promotion requires an independent anchor tying a particular bit
or branch outcome to a named release behavior.

## Pipeline

`tools/ghidra/run_memory_backend_evidence.sh` writes:

```text
memory_release_byte_behavior.json
```

from the same six-function instruction export already used for allocation/free
diagnostic slicing, so no additional Ghidra export pass is required.
