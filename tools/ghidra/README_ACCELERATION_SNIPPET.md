# Fast local query layer

After producing `out/shift_ghidra_database` with `run_shift_export.sh`, build the optional SQLite accelerator:

```bash
python3 tools/ghidra/build_shift_sqlite_index.py \
  out/shift_ghidra_database \
  out/shift_ghidra.sqlite
```

This index is for navigation and candidate discovery only. Rows must still be joined to exact PC-retail machine provenance before semantic promotion. Full workflow: `docs/DEVELOPMENT_ACCELERATION.md`.
