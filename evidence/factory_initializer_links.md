# Factory-to-initializer static evidence

This evidence layer narrows source-level factory relationships without
promoting every vtable-writing function to a C++ constructor.

## Extractor

`tools/shift_live_dump/extract_factory_initializer_links.py` joins three static
observations for every registered class that already has a unique PE vtable:

1. a source function references the class RTTI descriptor;
2. that same function directly calls another recovered `FUN_x` routine;
3. the called routine references the class's unique `PTR_FUN_<vtable>` symbol.

The target is emitted as an `initializer_candidate`. The format is
`SHIFT-FACTORY-INITIALIZER-LINKS/1`.

This intentionally does **not** claim constructor semantics. A routine may
write a class vtable during construction, destruction, reset, or another
lifecycle transition. The factory call narrows the role substantially, but
constructor naming still requires initialization/lifetime evidence.

## Independent Ghidra cross-check

With `--ghidra-export`, each source caller/target pair is independently checked
against direct `callgraph.jsonl` edges. The command exits non-zero when a
source-derived link is absent from the supplied Ghidra call graph.

The generic Ghidra `constructors.jsonl` and `factories.jsonl` candidate layers
are deliberately not used.

## Known track/path anchor

The existing track/path source verifier already proves two concrete source
links inside `FUN_006d8490`:

- `AISegmentPath`: descriptor `DAT_00c0d668` -> `FUN_006cfe70`
- `AIPolylinePath`: descriptor `DAT_00c0d608` -> `FUN_006cc900`

The direct Ghidra call graph independently records:

- `0x006d84b6 -> 0x006cfe70`
- `0x006d84db -> 0x006cc900`

These known links are useful calibration points because neither target is
present in the generic `constructors.jsonl` heuristic output. Absence from that
heuristic set is therefore not negative constructor evidence.

## Usage

```bash
python3 tools/shift_live_dump/extract_factory_initializer_links.py \
  /path/to/SHIFT.exe.c \
  --exe /path/to/SHIFT.exe \
  --ghidra-export out/shift_ghidra_database \
  --json-out out/factory_initializer_links.json
```

## Scope

The report does not establish allocation ownership, destructor symmetry,
constructor completeness, object lifetime, or gameplay semantics. It provides
a conservative bridge from class identity and a unique PE vtable to concrete
factory call sites and vtable-writing initializer candidates.
