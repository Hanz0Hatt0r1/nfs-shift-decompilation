# Process 1D — slot3 exact wheel-root persistence frontier

The remaining global alias blocker cannot be closed by searching only for field `+0x538`. A selected wheel pointer may first be copied, pushed, stored, or transformed and only later reach a writer/callback. This frontier adds a bounded capture specifically for the **exact wheel-root register lifetimes already proven by retail machine contracts**.

No new semantic identity is inferred by this tooling. It only inventories candidate persistence/escape instructions inside six pinned carrier windows.

## Bounded exact-root windows

| Function | Exact-root register | Window |
| --- | --- | --- |
| `FUN_00758b50` | `ECX` | `0x00758ccf .. 0x00758d70` |
| `FUN_00755950` | `EDX` | `0x00755956 .. 0x00755992` |
| `FUN_00755a60` | `ESI` | `0x00755a73 .. 0x00755f71` |
| `FUN_00752fc0` | `ECX` | `0x00752fc0 .. 0x00752fe5` |
| `FUN_00760b50` | `ESI` | `0x00760b6a .. 0x00760d63` |
| `FUN_00755f80` | `ESI` | `0x00755f80 .. 0x00756004` |

The exporter refuses function-name drift and emits only instructions in these windows that mention the exact-root register, plus call boundaries in the same window.

## Candidate classes

The analyzer ranks candidates in this order:

```text
memory-store-root          score 100
push-root                  score 90
register-copy-root         score 60
derived-address-root       score 50
call-boundary              score 25
root-based-memory-dest     score 10
root-based-memory-source   score 5
other-root-use             score 1
```

`memory-store-root` and `push-root` are inspected first because they can directly create longer-lived aliases or call arguments. They are still not persistence proof: destination ownership, later consumers, call argument position and selected slot3 identity must be proven independently.

## Run

In authoritative PC retail 1.02 Ghidra:

```text
ShiftExactWheelRootPersistenceExporter.java /path/to/p1d_exact_root_persistence.jsonl
```

Then:

```bash
python3 tools/ghidra/analyze_p1d_slot3_exact_root_persistence.py \
  /path/to/p1d_exact_root_persistence.jsonl \
  --output out/p1d_slot3_exact_root_persistence_frontier.json
```

The committed plan intentionally records `retail_export_captured=false`. Until an authoritative capture is added and every relevant positive candidate is adjudicated, these remain false:

```text
machine_register_alias_storage_ruled_out = false
callee_created_aliases_ruled_out = false
callbacks_registered_outside_carriers_ruled_out = false
stored_or_escaped_aliases_ruled_out = false
slot3_writer_provenance_proven = false
p1_3d_complete = false
```

Provider count remains 7.
