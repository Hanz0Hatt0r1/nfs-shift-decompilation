# Ghidra exporter source-to-runner inventory

**Repository snapshot:** `origin/main` at `e660406e2a55ef2c1bfaaa71f76e5dadad102522`  
**Audit date:** 2026-10-17

This inventory maps the checked-in `tools/ghidra/*Exporter.java` sources to
their shell entry points and documented manual use. It contains no binary
rows, addresses, labels, or runtime captures.

| Source | Checked-in caller or documentation | Shared relationship | Current boundary |
|---|---|---|---|
| `ShiftCompactInstructionStreamExporter.java` | `tools/ghidra/run_p1b_manager374_helper_setter_ghidra_headless.sh` | The runner prefers `revenginstr`'s compact-instruction-stream runner and uses this source as a fallback. | Retain as the compatibility fallback; the consumer bridge and output contract remain local. |
| `ShiftEvidenceExporter.java` | `tools/ghidra/run_shift_export.sh`; `tools/ghidra/README.md` | No single shared exporter currently replaces its complete bundle. It writes binary metadata, functions, callgraph, vtables, constructors, string xrefs, globals, static tables, switches, and factories. | Keep the bundle in NFS Shift. Map individual outputs to shared contracts before considering partial extraction. |
| `ShiftExactWheelRootPersistenceExporter.java` | `docs/PROCESS_1D_SLOT3_EXACT_ROOT_PERSISTENCE_FRONTIER.md` | No shared equivalent identified; documented as a manual Ghidra script. | Consumer-specific persistence query. |
| `ShiftFunctionInstructionExporter.java` | `tools/ghidra/run_shift_function_instructions.sh` | The runner prefers `ExportGhidraFunctionInstructions.java` and retains this source for older shared checkouts. | Compatibility fallback; keep the adapter and file contract in NFS Shift. |
| `ShiftGlobalReferenceExporter.java` | `tools/ghidra/run_shift_global_references.sh` | The runner prefers `ExportGhidraAddressReferences.java`. | Compatibility fallback; keep the output adapter and file contract in NFS Shift. |
| `ShiftInstructionSliceExporter.java` | `tools/ghidra/run_shift_instruction_slices.sh` | The runner prefers `ExportGhidraInstructionSlices.java`. | Compatibility fallback; keep the output adapter and file contract in NFS Shift. |
| `ShiftNativeResolutionPrimitiveExporter.java` | `docs/PROCESS_1D_CONTROLLER1_NATIVE_APC_PRIMITIVE_FRONTIER.md`; `docs/PROCESS_1D_CONTROLLER1_NATIVE_PRIMITIVE_REACHABILITY.md` | No shared equivalent identified; no checked-in shell caller found in this snapshot. | Consumer-specific native-resolution query. |
| `ShiftP13ASlot01TopologyAliasExporter.java` | `docs/PROCESS_1A_P13A_SLOT01_TOPOLOGY_ALIAS_FRONTIER.md` | No shared equivalent identified; no checked-in shell caller found in this snapshot. | Consumer-specific topology query. |
| `ShiftScalarUseExporter.java` | `tools/ghidra/run_shift_scalar_uses.sh` | The runner prefers `ExportGhidraScalarUses.java`. | Compatibility fallback; keep the output adapter and file contract in NFS Shift. |
| `ShiftWheelRuntimeAliasExporter.java` | `docs/PROCESS_1D_SLOT3_WHEEL_RUNTIME_ALIAS_FRONTIER.md`; `docs/PROCESS_1D_SLOT3_WHEEL_RUNTIME_ALIAS_INVENTORY.md` | No shared equivalent identified; no checked-in shell caller found in this snapshot. | Consumer-specific runtime-alias query. |

The five shared-first wrappers keep local Java fallbacks for environments where
the shared checkout is unavailable. Removing a fallback requires same-input
parity for its output contract and a caller review. The specialized persistence,
native-resolution, topology, and runtime-alias queries remain consumer-owned.
`ShiftEvidenceExporter` needs a table-by-table contract comparison because its
bundle combines several evidence families and project-local interpretations.

## Same-input parity follow-up (2026-10-18)

At NFS Shift main `c125488b`, the scalar-use wrapper and its local fallback were
run against the same analyzed `SHIFT.exe` for scalar `0x374`. Each produced 170
records with byte-identical adapted `SHIFT.GhidraScalarUses/1` output. The
targeted function-instruction wrapper and fallback were also byte-identical for
function `0x00451280`, covering one row with 2,962 instructions. Hash-only
reports and reproduction notes are in the
[parity evidence directory](ghidra_exporter_parity/). These results add
per-format parity fixtures; they do not retire the fallback or change the
inventory classification. The generic all-functions instruction-corpus mode
remains outside the compatibility exporter contract.
