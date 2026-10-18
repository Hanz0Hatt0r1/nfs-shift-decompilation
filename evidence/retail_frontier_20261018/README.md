# Retail direct-entry frontier — 2026-10-18

The merged [PR #2079](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/pull/2079) adds a structural direct CALL/JMP preflight and optional guest RAM write provenance. The v1 report below was generated from its preflight implementation against the shared whole-program compact stream and the frozen 41,538-function Ghidra corpus. The current branch extends it to v2 with direct conditional branches.

## Inputs and result

- Program: `SHIFT.exe`, language `x86:LE:32:default`.
- Compact stream SHA-256: `acb899970a0a0e6aaff012fe4c85fc7469fb153f290ee20b76723dc03c2e9501` (`/tmp/nfs-shift-compact-shared-20261018.jsonl.gz`; exporter parity report records matching shared/fallback instruction records).
- Function corpus SHA-256: `bc3f5a5972842f605b0bdd25dbc80b3129b96df30c3584d2dd31222aa5a454bc` (the hash recorded by the corpus manifest).
- Preflight report SHA-256: `bf99881de4a0d5e60f65b632f8b6f9bc32dd60a196b26c933d2395a4aaf863da`.
- Direct transfers: **241,709**; functions: **41,538**.
- Counts: 194,279 covered function entries; 44,157 same-function jumps; 188 jumps into another function's interior; 1,161 orphan direct targets; 1,924 targets outside the instruction stream.
- Candidate transfers: **1,349**, across **1,143 unique targets**.

The current startup frontier is a concrete `jump_into_other_function_interior`: `0x00509678` in function `0x0050966b` jumps to `0x00509588`, an instruction owned by function `0x005093a0`; `0x00509684` similarly jumps to `0x0050958c`. These are block entries, not independent Ghidra functions. The exact instruction slices for `0x00509551`, `0x00509588`, and `0x0050958c` are preserved as adjacent evidence files and lower to three exported P-code functions with zero rejected rows.

## Scope

The v1 preflight analyzes direct `CALL` and unconditional `JMP` flows only. The v2 report also includes direct conditional branches. Both exclude indirect transfers and same-function branches, and treat candidates as structural review targets rather than semantic proof. The full report is a review set, not a claim that every candidate is needed by startup.

The compact stream and full corpus are retained in the local artifact cache rather than duplicated in this evidence folder; hashes above bind this report to those inputs.

## Follow-up: conditional branch continuation

After adding the three direct JMP entries, the retail probe reached `0x0050968e` from the conditional `JZ` at `0x005095a8` (and equivalent branches at `0x005095b3`, `0x005095bd`, and `0x005095c7`). This is an interior continuation in Ghidra function `0x0050966b`, not a function start. PR #2079 intentionally preflights direct CALL/JMP only, so that edge was outside its v1 report. An exact `0x0050968e:0x25` instruction slice lowers cleanly as one supplemental P-code export; its build manifest is `pcode_supplement_build_0050968e.json`.

This gap motivated preflight format v2 in the current branch, which includes direct conditional branch targets while still excluding indirect transfers. The v2 full-corpus run produced **384,244** direct transfers across 41,538 functions: 184,695 covered function entries, 44,152 same-function unconditional jumps, 146,881 same-function conditional branches, 188 jumps into another function interior, 394 conditional branches into another function interior, 7,848 orphan direct targets, and 86 targets outside the instruction stream. It reports 8,430 candidate transfers across 6,617 unique targets. It identifies all four conditional edges to `0x0050968e` as `conditional_branch_into_function_interior` with owner `0x0050966b`. SHA-256: `44589080a11c286fb4308a819c18ee562259cebd3c111a780882bcfeb0f34cba`.

## Follow-up: indirect retail entry

After the conditional continuation was restored, probe v99 reached computed call target `0x0054be00` from guest function `0x0040ba50`. The Ghidra function exporter has no function starting at that address, but its exact instruction slice runs through the `RET` at `0x0054bef1` (`0xf2` bytes, 86 instructions). That slice lowers as one exported P-code function with no rejected instructions; the slice and build manifest are preserved as evidence. Because the target arrives through an indirect `CALL`, the static direct-control-flow preflight v2 intentionally does not list it. Runtime evidence remains necessary for this edge class.

The next probe after adding `0x0054be00` reached computed call target `0x0082db70`, another address without a Ghidra function start. The exact `0x0082db70:0x7` getter slice (`MOV EAX,[ECX+0x5ec]; RET`) lowers with zero rejections and is preserved with its build manifest. This entry also depends on runtime evidence rather than the direct-transfer preflight.

The next computed target was `0x0082f780`, also without a Ghidra function start. Its exact contiguous `0x2c9`-byte P-code slice covers 201 instructions, including its internal conditional branches and three return paths. The supplement builder accepted all 818 operations and rejected none; evidence and build manifest are preserved.

After restoring `0x0082f780`, the startup probe reached conditional continuation `0x0050c8a9` from function `0x0050c880`. Ghidra identifies the owning function at `0x0050c8a3`; the continuation is the `XOR AL,AL; POP ESI; RET` tail after an indirect call. The exact `0x0050c8a9:0x4` instruction slice lowers to one exported P-code function with zero rejected operations. The slice and build manifest are preserved.

With `rvi_0050c8a9` loaded, the entrypoint probe advanced past the prior missing-export failure. The `/dev/null` mesh variant then stopped while parsing the deliberately empty scene input, after the guest entrypoint call returned without a P-code error. An initial run with a generated MGEO from the retail `Alpental.bff` rendered one frame, but the guest entry point remained active. Its complete input/output record is `entrypoint_probe_v104.json`.

## Follow-up: cooperative guest scheduler and Vulkan frames

The frame-loop diagnostic now records the main guest thread state and host loop exit reason. It showed the guest scheduler yielding at `0x006472d0`; Ghidra's existing decompilation shows that function begins with `SwitchToThread`. After 120 host frames, the main guest thread remained runnable, with four workers waiting and one ready thread. That is observed scheduler state; the PE entry point remains incomplete.

The 120-frame run initially stopped on `VK_SUBOPTIMAL_KHR`. Vulkan permits the acquired image to be presented in this state, so the runtime now continues through suboptimal acquire/present results and only stops on `VK_ERROR_OUT_OF_DATE_KHR`. The probe then rendered all 120 requested frames with status `ok`, no runtime error, and 80,626 dispatches across 1,417 unique guest functions. This uses converted `Alpental` MGEO as smoke geometry; it does not establish retail D3D9 rendering or a playable game. The complete run record and raw runtime output are `entrypoint_probe_v110.json` and `shift-probe-v110.log`.
