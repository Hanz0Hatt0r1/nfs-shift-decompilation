# BODY writer bridge candidates joined to the proven callgraph frontier

`tools/ghidra/join_body_writer_candidates_to_frontier.py` connects the p-code
access-pattern report `SHIFT.BodyWriterBridgeCandidates/1` to
`SHIFT.GhidraProvenCallgraphFrontier/1`.

Output format:

```text
SHIFT.BodyWriterBridgeFrontierJoin/1
```

The join is intentionally contextual only. It does not turn an offset-pattern
candidate into a BODY writer or integrator.

## Why this join exists

The bridge classifier can find a function that, on one syntactic base register,
reads the frozen BODY accumulator offset group and writes the frozen motion-side
group, or reads motion-side offsets and writes origin/basis offsets. That is
still insufficient on its own: the same offsets may occur in unrelated object
layouts.

The proven callgraph frontier supplies an independent target-selection axis. A
candidate can now be described as one of:

- `proven-slice-root`: the function is already part of the proven physics or
  vehicle subsystem slice used as a callgraph root;
- `callgraph-frontier`: the function lies within the selected direct-callgraph
  frontier and preserves its `min_depth`, connected subsystems and direct edge
  context;
- `outside-selected-frontier`: the offset pattern exists but the current
  physics/vehicle frontier does not connect it within the chosen depth.

No numerical score or winner is produced.

## Preserved frontier evidence

For a frontier candidate the joined row retains:

- shortest direct-callgraph depth;
- connected selected subsystems;
- adjacent proven-slice addresses;
- exact candidate -> slice calls;
- exact slice -> candidate calls;
- direct incoming/outgoing counts;
- `multi_anchor_caller_candidate`;
- unresolved indirect-call sites.

For proven-slice roots the join reports depth zero and selected subsystem
membership. Root-level unresolved indirect-call blockers are retained as well.

## Run

```bash
python3 tools/ghidra/join_body_writer_candidates_to_frontier.py \
  out/body_writer_bridge_candidates.json \
  --frontier out/physics_vehicle_callgraph_frontier.json \
  --json-out out/body_writer_bridge_frontier_join.json
```

`--fail-on-outside` can be used for a deliberately closed investigation where
every offset-pattern candidate is expected to lie in the current frontier.
`--fail-on-malformed` rejects malformed candidate rows while keeping them visible
in a normal report.

## Intended next step

The most useful follow-up candidates are those for which independent ABI/call-site
evidence can prove what object pointer the matching base register carries at the
function boundary. A direct-frontier or multi-anchor relationship makes that
analysis easier to prioritize, but it is not itself pointer provenance.

For Process B, the desired proof remains one of these forms:

```text
proven BODY pointer
  -> same-register accumulator reads
  -> same-register motion/cross writes
```

or:

```text
proven BODY pointer
  -> same-register motion/cross reads
  -> same-register origin/basis writes
```

followed by a separately proven update-order relationship around the vehicle and
solver/contact frame.

## Evidence boundary

This layer does not prove:

- BODY/vehicle/wheel pointer identity;
- aliasing across functions;
- subsystem membership for a frontier candidate;
- that a multi-anchor caller is an update loop;
- persistent state mutation between frames;
- timestep ordering;
- position/orientation integration mathematics.

Every joined candidate therefore remains `body_writer_proven=false` and
`promoted=false` until those independent proofs are available.
