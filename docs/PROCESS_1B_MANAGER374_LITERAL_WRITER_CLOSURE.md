# Process 1B — complete literal `manager+0x374` writer closure

## Blocker removed

P1.3B must decide whether `manager+0x374` can acquire fixed `HDVehicle+0x4330`. The complete PC-retail machine inventory contains 25 instructions whose memory destination itself carries literal displacement `+0x374`. Until every receiver/value path is classified, the final identity join must remain fail-closed.

The raw authoritative `SHIFT.exe` is now available and SHA-256 matches the long-pinned PC retail 1.02 identity:

```text
eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1
```

A fresh GNU objdump scan independently reproduces the merged 25-site inventory.

## Correction to the old last-site frontier

`SHIFT.HDVehicle64e8Manager374FinalPreclusterRejections/1` incorrectly treated `0x00864c67 mov esi,[ebx+0x8]` as the surviving base of target store `0x00865013`.

Retail machine bytes prove otherwise:

```text
0x00864c40  mov edi,ecx
0x00864c42  mov [ebp-0x34],edi
... temporary first-stack-argument use ...
0x00864d63  mov esi,[ebp-0x34]
... temporary REP-MOVS source cursor ...
0x00864db5  mov esi,[ebp-0x34]
... no later ESI write ...
0x00865013  fstp DWORD PTR [esi+0x374]
```

The corrected machine window `0x00864c40..0x00865018` is 985 bytes with SHA-256:

```text
8ae83797d2f0a6bd6120737d84df25ce8a50ff1f4ad35122997277e2acea033a
```

Therefore the target base is entry `ECX` / `this`, not the first stack argument.

Whole-image direct-call recovery gives exactly two callers of `FUN_00864c10`:

- `0x0085b6f2` in `FUN_0085b6e0`, preserving entry `ECX` to the call;
- `0x0085c38f` in `FUN_0085c370`, restoring `ECX` from saved entry `ESI` before the call.

Both are slots `+0x18/+0x1c` of vptr `0x00b1d508`, published by constructor store `0x0085afda`. This vptr is distinct from Participants Manager root/subobject vptrs `0x00ab9190` / `0x00ab916c`. Thus `0x00865013` cannot be a Participants Manager `+0x374` writer.

The corrected contract is `SHIFT.HDVehicle64e8Manager374FinalPreclusterRejections/2`.

## Exact 25-site partition

`SHIFT.P1B.Manager374LiteralWriterClosure/1` composes five disjoint partitions:

| Partition | Sites |
|---|---:|
| Proven manager-domain writes already value-rejected | 2 |
| Inherited closed-negative receiver domains | 3 |
| Exact vptr/owner/allocation receiver rejections | 15 |
| Corrected precluster rejections | 2 |
| FMOD DSP Codec callback-derived receiver rejections | 3 |
| **Total** | **25** |

The composer verifies pairwise disjointness and exact equality with the machine inventory. Remaining literal sites: **0**.

## Gate effect

Promoted:

```text
literal_plus_0x374_writer_surface_complete = true
literal_manager_374_receiver_provenance_complete = true
literal_plus_0x374_site_can_place_fixed_hdvehicle_4330 = false
```

Still fail-closed:

```text
computed_address_manager_374_writer_surface_complete = false
global_helper_non_vtable_indirect_setter_surface_complete = false
global_manager_root_origin_surface_complete = false
manager_374_join_to_hdvehicle_4330_complete = false
last_literal_0x004b86cf_rejected = false
p1_3_control_producer_complete = false
external_provider_count = 7
```

## Boundary

This closure is deliberately limited to instructions whose memory destination itself contains literal `+0x374`. It does not absorb materialized/computed address writers, helper-mediated setters, runtime pointer aliases, external mutation, generated code or arbitrary process memory.

## Reproduction

Verify the corrected last site against authoritative retail bytes:

```bash
python3 tools/ghidra/analyze_p1b_manager374_last_literal_receiver.py /path/to/SHIFT.exe
```

Rebuild the aggregate contract:

```bash
python3 tools/ghidra/build_p1b_manager374_literal_writer_closure.py \
  --json-out /tmp/p1b_manager374_literal_writer_closure.json
cmp /tmp/p1b_manager374_literal_writer_closure.json \
  evidence/p1b_manager374_literal_writer_closure.json
```

## Next step

Run the already-merged materialized/computed `+0x374` probes on authoritative retail `SHIFT.exe`, classify their actual positive candidates, and only then revisit the final `manager+0x374 -> HDVehicle+0x4330` identity join and `0x004b86cf`/slot2 adjudication.
