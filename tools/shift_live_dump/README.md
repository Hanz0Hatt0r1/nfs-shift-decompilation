# shift-live-dump

Non-stopping Linux memory snapshots for Need for Speed: SHIFT running under Wine or native Linux.

The primary path is Linux `process_vm_readv(2)`. The tool does not ptrace-attach the target and does not intentionally stop it. In `auto` mode it also opens `/proc/PID/mem` as a fallback when the kernel permits it.

## Build

```bash
make -C tools/shift_live_dump
```

## Commands

Inspect mappings:

```bash
./tools/shift_live_dump/shift-live-dump maps <PID>
```

Capture writable memory:

```bash
./tools/shift_live_dump/shift-live-dump snapshot <PID> captures/shift-0001
```

Capture other regions with `--regions all|heap|anonymous|writable|modules`.

Use repeated snapshots while the scene is running:

```bash
./tools/shift_live_dump/shift-live-dump watch <PID> captures/garage \
  --interval-ms 250 --count 20 --regions writable
```

Compare snapshots without loading whole regions into RAM:

```bash
./tools/shift_live_dump/shift-live-dump diff \
  captures/garage/snapshot-000000 \
  captures/garage/snapshot-000019 \
  captures/garage-diff
```

Default block size is 4 KiB.

## Output

Each snapshot contains `manifest.json`, `maps.txt` and `regions/*.bin`. Region files are exactly the mapped size; bytes that could not be read are zero-filled and accounted for as `bytes_failed` in the manifest.

The manifest records PID, selector, page size, backend, mapping boundaries, permissions, path and read statistics.

## Evidence limits

A live snapshot is not an atomic process-wide state. SHIFT can mutate memory while the tool is reading it. Use the snapshots to locate stable structures, pointers, tables, state transitions and memory correlations; do not treat a multi-structure snapshot as proof that all values existed simultaneously.

Kernel ptrace-related access restrictions still apply. Start with SHIFT and the dumper under the same user. The tool does not weaken those protections.
