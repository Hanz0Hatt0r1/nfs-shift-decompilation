# Phase 348: streaming BMW extraction from apitrace

The confirmed working runtime source for the Linux research setup is the existing
\`apitrace\` D3D9 trace. Phase 348 adds a bounded extractor that reads a .trace
without first generating a multi-gigabyte text dump on disk.

## Command

    python tools/extract_apitrace_unique_bmw.py \
      /path/to/shift.trace \
      /path/to/bmw-apitrace-evidence \
      --auto-trim

\`apitrace dump\` is consumed as a streaming subprocess. The extractor keeps only
the D3D9 state needed to identify BMW geometry draws and their resource lifecycle.

The default BMW target is 3,550 vertices with the six known primitive counts:

- 28
- 50
- 192
- 204
- 2,098
- 2,462

The primitive list can be overridden with \`--primitive-counts\`.

## Output

The extractor emits:

- \`unique_bmw_geometry.json\` — versioned report with unique draw-state
  fingerprints, representative calls, VB/IB pointer identity and creation
  instances;
- \`compact_relevant_calls.txt\` — only the relevant Create/Set/draw call lines;
- \`callset.txt\` — compact call numbers for manual
  \`apitrace dump --calls=@callset.txt\`;
- \`summary.json\` — bounded scan totals and extraction status.

With \`--auto-trim\` and a .trace input it also runs:

    apitrace trim --auto --calls=<representative-draw-calls> \
      -o bmw_unique.trace /path/to/shift.trace

The resulting \`bmw_unique.trace\` is the preferred artifact to inspect or transfer
when the full trace is too large. \`--auto-trim\` is deliberately not attempted for
plain text dumps.

## Deduplication and identity

Geometry fingerprints include:

- vertex declaration pointer and its creation instance;
- every active vertex stream pointer, creation instance, offset and stride;
- index-buffer pointer and its creation instance.

A reused COM pointer is not treated as the same resource after a \`Release\`
boundary. Each representative geometry record therefore remains tied to the
active creation instance at the target draw.

The tool stores only bounded lifecycle call samples for VB/IB \`Lock\`, \`Unlock\`,
\`GetDesc\` and \`Release\`; it does not copy mapped buffer payloads out of the
text dump.

## Evidence boundary

This phase proves only runtime draw/state and resource-instance evidence. It does
not promote an apitrace text line into exact VB/IB byte parity.

The next proof remains:

    BMW MEB candidate
        ↓
    runtime VB/IB resource instance
        ↓
    exact payload bytes
        ↓
    SHA-256 / byte-for-byte parity

If \`bmw_unique.trace\` is produced successfully, it can be used as the compact
source for the next extraction stage without re-running the game.
