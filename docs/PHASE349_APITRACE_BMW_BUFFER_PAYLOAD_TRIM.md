# Phase 349: lock-aware BMW apitrace payload trim

Phase 348 reduced the 2.9 GiB runtime trace to the six verified BMW geometry
resource instances. Phase 349 prepares a second compact trace that also retains
the active \`Lock/Unlock\` lifecycle for the verified BMW VB and six INDEX16 IBs.

This matters because apitrace's D3D9 tracer records mapped buffer contents when a
buffer is unlocked; the generated trace therefore carries the upload bytes even
though ordinary \`apitrace dump\` output does not print them as a large text blob.
The upstream D3D9 tracer explicitly copies mapped buffer memory during \`Unlock\`.
See the apitrace D3D9 tracer implementation in the upstream apitrace repository.

## Command

Starting from the Phase 348 output:

    python tools/prepare_apitrace_bmw_buffer_payload_trim.py \
      /path/to/shift.trace \
      /path/to/bmw-apitrace-evidence/unique_bmw_geometry.json \
      /path/to/bmw-apitrace-payload \
      --trim

The tool reuses the verified creation instances from the Phase 348 report and
filters lifecycle calls to the active resource lifetime. When lifecycle fields
are missing in the report, it performs only a bounded \`apitrace dump\` window
around each creation call instead of scanning the full trace again.

## Output

    bmw-apitrace-payload/
    ├── bmw_buffer_payload_plan.json
    ├── bmw_buffer_payload_callset.txt
    ├── bmw_buffer_payload.trace
    └── summary.json

The callset includes the existing representative BMW draw/state calls plus the
active \`Lock\`, \`Unlock\` and \`GetDesc\` calls for the verified VB/IB creation
instances.

The trimmed trace is intended for the next extraction stage. It is deliberately
not called byte-parity evidence until the payload bytes are independently
recovered and compared with the exact MEB-derived candidates.

## Why this avoids another full scan

Phase 348 already established the exact BMW resource creation call numbers. The
payload planner uses those call numbers directly. Its only trace inspection is a
small creation-local window when the Phase 348 report lacks lifecycle metadata.
The final trim uses apitrace's supported \`--calls=@file\` syntax. citeturn175388search3

## Evidence boundary

This phase establishes that the compact trace contains the D3D9 buffer upload
calls necessary for payload recovery. It does not assume that text dumping is a
byte extractor; exact byte identity remains a separate check.

## Fake memcpy payload calls

An apitrace D3D9 buffer Unlock emits a separate fake `memcpy` call. The fake
call carries the mapped bytes as a `TYPE_BLOB`. Therefore a trim callset that
contains only the outer Unlock would discard the payload.

Phase 349 now performs a bounded dump around each active Unlock and adds the
corresponding fake `memcpy` call numbers to the callset. The plan records them
as `fake_memcpy_calls_by_unlock` and blocks `ready_for_payload_trim` when an
active Unlock has no discovered fake memcpy call.

This keeps the full-trace scan out of the workflow while preserving the actual
payload-bearing calls needed by Phase 350.

