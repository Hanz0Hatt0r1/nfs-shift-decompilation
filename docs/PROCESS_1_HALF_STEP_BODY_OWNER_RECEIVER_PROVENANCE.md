# Process 1 — FUN_00765470 -> FUN_007b2270 receiver provenance

## Playable-slice blocker

Process 1 PR #1194 proves that the normal outer-update receiver
`&DAT_00c13700` is independently the recovered global vehicle component base.
It also corrects the earlier requirement that the anonymous `*record+0x340`
update child must equal the vehicle pointer.

Process 1 #1188 and Process 2 Phase 702 already prove the BMW chassis as BODY 0,
while Phase 698/700 can transport a proven BODY pose. Process 3 Phase 645 now
also supplies the exact resource-side VHF bind transform and SVWT matrix
convention.

The remaining identity edge before a positive persistent BODY0 pose is therefore
narrower:

```text
DAT_00c13700
  -> FUN_00770e80 receiver
  -> FUN_00765470 entry receiver
  -> CALL 0x0076582a
  -> FUN_007b2270 BODY-array owner receiver
```

Existing source evidence already shows the outer update calling
`FUN_00765470(this, ...)`. The missing committed evidence is operand-level
receiver provenance at `0x0076582a`.

No original game execution and no new runtime capture are required.

## New analyzer

```text
tools/ghidra/analyze_fun_00765470_body_owner_receiver.py
```

Output contract:

```text
SHIFT.Fun00765470BodyOwnerReceiverProvenance/1
```

Input must be exactly one:

```text
SHIFT.GhidraFunctionInstructions/2
```

row for `FUN_00765470` at `0x00765470`.

The analyzer requires the exact machine call:

```text
0x0076582a -> 0x007b2270
```

before any positive result is possible.

## All-path physical-register proof

The proof target is intentionally physical:

```text
ECX immediately before CALL 0x0076582a
    ==
ECX at FUN_00765470 entry
```

on every reachable intraprocedural path.

The analyzer constructs a CFG from Ghidra fallthrough/flow metadata and performs
a finite register-provenance fixed point over:

```text
EAX EBX ECX EDX ESI EDI EBP
```

It tracks exact register copies and simple identity-preserving LEA operations.
Arithmetic/register mutation becomes a derived value instead of being silently
preserved.

Direct CALLs invalidate IA-32 caller-saved:

```text
EAX ECX EDX
```

while allowing preserved-register transport such as:

```text
MOV ESI, ECX
...
CALL helper
...
MOV ECX, ESI
CALL FUN_007b2270
```

Structured p-code is a safety net. If Ghidra reports a tracked register output
for an instruction not handled by the audited transfer rules, that register is
invalidated as `unmodelled-pcode-write`.

Branches merge provenance sets. A positive result requires the exact singleton:

```text
receiver_origins_before_body_loop_call = ["entry:ECX"]
```

Any alternate origin, memory load, derived value, unknown call clobber or
multi-path disagreement keeps the proof fail-closed.

## One-command read-only export

The generic instruction exporter already exists, so this phase does not create a
second exporter. The wrapper only targets the one function required by the
current blocker:

```bash
GHIDRA_HOME=/opt/ghidra \
bash tools/ghidra/run_fun_00765470_body_owner_receiver.sh \
  /home/pes/ghidra_projects/shift \
  shift \
  SHIFT.exe \
  out/fun_00765470_body_owner_receiver
```

The script performs Ghidra analysis/export against the existing project. It does
not launch `SHIFT.exe`.

Outputs:

```text
fun_00765470_instructions.jsonl
fun_00765470_body_owner_receiver.json
```

## Current status

The repository already freezes:

- the `FUN_00770e80 -> FUN_00765470` half-step order;
- the source-level outer call as `FUN_00765470(this, ...)`;
- the `0x0076582a -> FUN_007b2270` direct call;
- BODY owner fields `+0x10` count and `+0x14` array pointer;
- BODY stride `0x170`;
- the persistent `FUN_007b2270 -> FUN_007bab70` writer path;
- global vehicle component base `0x00c13700` from PR #1194.

What is not committed yet is the exact `FUN_00765470` instruction/p-code row
needed to prove which value is in ECX at `0x0076582a`.

Therefore this phase is infrastructure for the nearest blocker, not a semantic
promotion. Until a retail instruction row produces the exact singleton
`entry:ECX`, keep:

```text
outer_receiver_to_BODY_owner_continuity_proven = false
vehicle_BODY_selection_ready = false
phase698_positive_selection_admissible = false
```

## Handoff after a positive retail result

A positive result is sufficient for the next composition step, but not by
itself for Phase 698. Process 1 must compose:

```text
SHIFT.GlobalVehicleComponentBaseIdentity/1
+ SHIFT.Fun00765470BodyOwnerReceiverProvenance/1
+ proven BMW chassis BODY 0
```

Only that composed contract should replace the obsolete Process 2 Phase 703
`update-child == vehicle-base` proof input.

The corrected identity chain would then be:

```text
0x00c13700 global vehicle/outer receiver
  -> same receiver enters FUN_00765470
  -> same ECX enters FUN_007b2270 BODY-array owner
  -> BODY domain includes proven chassis BODY 0
  -> Phase 698/700 persistent BODY0 pose
```

The next cross-process blocker after that is the narrower Phase 645 frame join:

```text
BODY0 pose frame <-> VHF vehicle-root/body-MEB frame relationship
```

not renderer object rediscovery.

## Regression coverage

`tests/test_ghidra_fun_00765470_body_owner_receiver.py` covers:

- preserved-register ECX continuity across helper calls;
- two branch paths converging on the same entry ECX;
- divergent branch provenance rejection;
- caller-saved ECX invalidation after CALL;
- unmodelled structured p-code register writes;
- instruction-export version rejection;
- exact body-loop CALL target rejection.

Synthetic positive fixtures test the analyzer only. They are not retail proof.
