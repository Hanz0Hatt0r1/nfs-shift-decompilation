# SHIFT release pointer backend chain

`tools/ghidra/analyze_release_pointer_chain.py` connects the independently
recovered pool-free diagnostic `%p` input back through the retail release backend
chain.

The output format is `SHIFT-MEMORY-RELEASE-POINTER-CHAIN/1`.

## Evidence chain

The analyzer starts only when
`SHIFT-MEMORY-FREE-DIAGNOSTIC-SLICE/1` has already proven one physical entry
storage of `FUN_00657c30` as the value printed by `%p` in:

```text
Error freeing small alloc (no head) '0x%p' from pool: '%s'
```

It then follows two physical forwarding hops from the targeted instruction
export:

```text
0x0064f4c0 (release thunk)
  -> FUN_0064f3a0
  -> FUN_00657c30
```

For the `FUN_0064f3a0 -> FUN_00657c30` call, the exact callee storage identified
by the free diagnostic is mapped backwards through register setup or a directly
recoverable stack `PUSH` to one physical entry storage of `FUN_0064f3a0`.

That resulting storage is then mapped through the `0x0064f4c0` transfer to one
physical entry storage of the release thunk. A successful artifact therefore
records:

```text
free_pointer_storage
release_backend_pointer_storage
release_thunk_pointer_storage
release_pointer_chain_proven = true
```

## Fail-closed behavior

The chain remains unproven when:

- the free diagnostic `%p` storage is not independently proven;
- there is not exactly one direct transfer for a required hop;
- a volatile register crosses an unmodelled call;
- an unsupported register write prevents exact backtracking;
- a required stack argument cannot be tied to a unique `PUSH`;
- a tail transfer would require stack-parameter remapping.

The last restriction is intentional. Register-preserving tail transfers can be
proved directly; stack remapping across an arbitrary tail transfer requires a
stronger ESP-state model and is left closed rather than guessed.

## Semantic boundary

A positive backend chain proves that one physical release-thunk input is the
value that eventually reaches the `%p` slot of the retail free diagnostic. It
does **not** yet assign that role to a wrapper or recovered-source argument.
That final promotion must join `release_thunk_pointer_storage` with the existing
wrapper/source argument provenance.

The chain also does not interpret `DL`. In particular it does not prove:

- release flag semantics;
- delete-kind semantics;
- scalar-vs-array delete behavior;
- compiler `operator delete` identity;
- ownership/lifetime policy.

Those remain independent evidence questions even if the released-pointer path is
fully recovered.
