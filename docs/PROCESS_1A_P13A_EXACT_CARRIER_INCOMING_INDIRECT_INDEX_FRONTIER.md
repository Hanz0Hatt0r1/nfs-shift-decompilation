# Process 1A / P1.3A — incoming indirect index frontier

## Scope

The merged exact-carrier callback work bounds indirect calls *originating from* carriers and finite static carrier-code-pointer tables. The complementary question is incoming indirect entry: can the Drive Ghidra call index resolve an indirect edge whose target is one of the 16 exact carriers?

This pass measures the capability of the current `shift_ghidra.sqlite` directly. It is navigation evidence only.

## Drive result

Authority:

```text
format   SHIFT.GhidraSQLiteIndex/1
SHA-256  ffcee0fe527563db7b74d17533164e2256ebd5fe6296a1deef4117f80dde732e
carriers 16
```

Call surface:

```text
all call records                    200,598
indirect=true edges                  19,500
indirect edges with resolved target       0
indirect edges with unresolved target 19,500
resolved incoming exact-carrier hits      0
```

The important conclusion is **not** “no incoming indirect carrier entry.” The current index supplies no resolved target for any indirect edge. Therefore the zero exact-carrier hit count is vacuous as an absence proof.

A synthetic regression verifies that if an indirect record does carry a resolved target equal to an exact carrier, the analyzer reports it.

## Gate

```text
incoming-indirect index frontier captured              = true
index has resolved indirect-target coverage             = false
resolved incoming exact-carrier hit found               = false
index can prove incoming exact-carrier absence           = false
incoming indirect entry ruled out                       = false
runtime callback registration ruled out                 = false
runtime-generated/copied carrier pointers ruled out     = false
runtime-generated selected-wheel stores ruled out       = false
stored-or-escaped aliases ruled out                     = false
slot0 complete                                          = false
slot1 complete                                          = false
P1.3 complete                                           = false
provider count                                          = 7
```

## Limits

This result is deliberately fail-closed. It does not classify:

- machine-level indirect branch targets;
- vtable dispatch resolved only at runtime;
- callback registration and later invocation;
- copied/encoded/reconstructed code pointers;
- selected-wheel data-pointer persistence.

The current SQLite index remains useful for callgraph navigation, but its unresolved `indirect=true` rows cannot be used to infer absence of an incoming carrier callback.

## Reproduce

```bash
python3 tools/ghidra/analyze_p1a_exact_carrier_incoming_indirect_index.py \
  /path/to/shift_ghidra.sqlite \
  --output evidence/p1a_p13a_exact_carrier_incoming_indirect_index_frontier.json
```

## Next step

Recover incoming indirect targets from machine/vtable/registration dataflow rather than from unresolved SQLite rows. Any positive carrier registration must be joined to its eventual indirect consumer before the callback/indirect-entry gate can change.
