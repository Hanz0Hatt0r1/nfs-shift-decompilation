# PC retail PE named exports: address anchors, not verified function contracts

## Provenance

Input is the original **Need for Speed: SHIFT PC retail 1.02** \`SHIFT.exe\`, SHA-256
\`eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1\`.
The binary is intentionally not committed to Git.

Direct PE32 export-directory analysis yielded:

- PE ImageBase: \`0x00400000\`
- Export directory name: \`GeckoFnl.exe\` (the export name inside \`SHIFT.exe\`)
- Export Address Table entries: **509**
- Named exports: **509**
- Unique exported virtual addresses: **375**
- Repeated name-to-address associations: **134**
- All observed named targets are code candidates in the PE's \`.text\` region.
- No forwarders in this executable's named export table.

The 509 export names are real decorated MSVC symbol strings, useful as *possible*
function-name anchors. This does **not** mean there are 509 independent function
implementations, nor does an export name prove class layout, engine identity, or
the machine-code behavioral contract. Identical RVA entries often represent aliases
or shared implementation/stub addresses.

## Generate the catalog

Run on the workstation with the exact retail executable:

\`\`\`sh
python3 tools/ghidra/export_shift_named_pe_symbols.py \
  '/path/to/SHIFT.exe' \
  --output-dir /tmp/shift-pe-export-anchors
\`\`\`

Outputs:

- \`shift_named_exports.csv\`: ordinal, decorated name, RVA, absolute VA, section,
  kind, forwarder.
- \`shift_named_exports_report.json\`: hash-locked counts and limitations.

To do an **exact address** join against the repository's frozen 41,538-function
Ghidra inventory:

\`\`\`sh
python3 tools/ghidra/export_shift_named_pe_symbols.py \
  '/path/to/SHIFT.exe' \
  --output-dir /tmp/shift-pe-export-anchors \
  --inventory '/path/to/shift.functions.tsv.gz'
\`\`\`

The frozen Ghidra function inventory is deliberately stored **outside Git**, as
documented in \`docs/PROCESS_0_FULL_FUNCTION_PORTABLE_CORPUS.md\`. Its expected SHA-256
is \`8b8b00d8493dba459edf186869ddf492dc26002af3b65d08b6988dc91a87fa24\`.
The resulting \`shift_exports_ghidra_exact_join.csv\` marks each export
\`exact_entry_match\` or \`not_in_frozen_entry_inventory\`; nonmatches must not be
silently assigned to the nearest function. The JSON report records exact-match
counts. A missing exact entry is **not proof of absent executable code**:
export thunks, alias entries and different function-boundary decisions are possible.

No corpus-wide exact-match count is asserted in this record, because the frozen
inventory was not present in the evaluation environment.

## Integration policy

Use \`exact_entry_match\` rows as **annotations** in Ghidra/revenginstr.
Preserve original PE decorated names, ordinals, RVAs, VAs, and source SHA-256.
Do not automatically rename functions in the retail corpus or translate decorated
signatures into inferred C++ class layouts. Before admitting a stronger type/
behavior claim, verify actual calling convention, disassembly/P-code, and object
layout and record evidence separately.

An exported decorated identifier is a named entry anchor, not a proof that
the function is unique, not a proof of subsystems (Apt vs other UI libraries),
and not a substitute for the existing deterministic P-code lowerer.
