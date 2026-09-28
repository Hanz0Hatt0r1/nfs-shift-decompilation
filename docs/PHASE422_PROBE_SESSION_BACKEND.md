# Phase 422 — frame-aware SDF probe session

The probe session bridge now accepts the optional `frame_entry_XXXXXX.json` record produced at `FUN_007b3f40`.

## Consistency checks

The session validates scalar-count equality between frame-entry and pre-solve captures, and requires the frame indices to match across frame-entry, pre-solve and post-solve records when all are present.

A frame-entry record with `backend=provider` is explicitly rejected for a builtin pre-solve session, because `FUN_007b0f20` is then bypassed and its pre-solve matrix dump cannot represent the selected backend.

The CLI accepts `--frame frame_entry_XXXXXX.json`. Numeric comparison remains focused on the existing pre-solve matrix/RHS and post-solve vector; the frame-entry record is an execution/backend consistency gate.
