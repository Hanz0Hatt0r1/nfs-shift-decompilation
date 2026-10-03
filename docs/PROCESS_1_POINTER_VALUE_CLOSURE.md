# Process 1 — pointer-value closure graph

The preceding Process 1 blocks intentionally prove pointer provenance one static
boundary at a time:

```text
receiver callsite
<- local receiver source
<- local base-register origin
<- function-entry register
<- exact parent callsite register
<- parent local source / parent entry register
<- ...
```

This block adds a composition layer that turns those independently audited
reports into one machine-readable graph without creating any new def-use facts.

Tool:

```text
tools/ghidra/build_vehicle_pointer_value_closure.py
```

Output:

```text
SHIFT.VehiclePointerValueClosure/1
```

## Inputs

The graph consumes:

```text
SHIFT.VehicleReceiverProvenance/1
SHIFT.VehiclePointerOriginFrontier/1
zero or more SHIFT.VehicleParentCallsiteTransfer/1 reports
```

Example:

```bash
python3 tools/ghidra/build_vehicle_pointer_value_closure.py \
  out/vehicle_receiver_provenance.json \
  out/vehicle_pointer_origin_frontier.json \
  out/vehicle_parent_transfer_depth1.json \
  out/vehicle_parent_transfer_depth2.json \
  --json-out out/vehicle_pointer_value_closure.json \
  --targets-out out/vehicle_pointer_value_next_targets.txt
```

The parent-transfer arguments are optional. With none supplied, the report
still produces the receiver/local-origin graph and keeps the parent targets from
the pointer-origin frontier unresolved.

## Graph direction

Edges point from an older/source value toward the later consumer closer to
`FUN_007155e9`.

Current relation kinds are:

```text
base-origin-to-receiver-source
receiver-source-to-callsite-register
parent-source-to-callsite-register
call-boundary-register-transfer
```

Typical graph fragment:

```text
parent [EDI+0x20]
  -> parent ECX at exact CALL
      -> child entry ECX
          -> child [ESI+0x40]
              -> receiver register at exact FUN_007155e9 callsite
```

Each edge imports the evidence state from the lower-level report that proved
that boundary. Graph connectivity itself never strengthens that state.

## Node identities

Nodes are intentionally syntactic and address-based:

```text
function-entry register
exact callsite register
register-relative memory/address source
```

The IDs include the function, exact instruction where relevant, register and
memory displacement where relevant. They are not class/object IDs.

## Cross-check with receiver provenance

Every pointer-origin callsite must exist in
`SHIFT.VehicleReceiverProvenance/1` with the same `(caller, call instruction)`.
A stale pointer-origin report therefore cannot silently attach to a different
receiver callsite.

The receiver edge imports the original receiver-definition evidence state.

## Iterative parent-transfer composition

Every parent-transfer report contributes:

```text
parent source -> parent callsite register -> child entry register
```

The composer may receive multiple depth reports. Parent functions that have
already been analyzed by any supplied transfer report are removed from the
current worklist.

The current frontier is the union of:

- `next_instruction_export_addresses` from the pointer-origin report;
- next targets from every parent-transfer report;

minus functions already present as analyzed parent functions in the supplied
transfer set.

This makes repeated static passes deterministic and avoids manually tracking
which parent level has already been consumed.

## Static endpoints

A graph node with no incoming provenance edge and at least one outgoing edge is
reported as a current static endpoint.

Examples include:

- a p-code-backed register-relative load/address whose base has not yet been
  expanded;
- a function-entry register for which no parent-transfer report is supplied.

A static endpoint is a chain boundary, not a semantic identity. In particular:

```text
static endpoint != owner
static endpoint != allocation root
static endpoint != vehicle object
```

## Evidence aggregation

The report exposes `weakest_graph_evidence_state`. This is the weakest imported
edge state across the composed graph.

It is an audit property only. It is not a confidence score and does not convert
multiple inferred/verified edges into a stronger semantic conclusion.

## Source conflicts

If composition finds more than one distinct static source feeding the same exact
callsite-register node, it emits:

```text
multiple-static-sources-for-one-callsite-register
state = ambiguous
```

No source is selected by ordering, path length, address, or report order.

This catches inconsistent targeted exports, incompatible analysis passes, or
real control-flow ambiguity that requires a stronger SSA/CFG proof.

Use:

```bash
--fail-on-source-conflict
```

when a downstream artifact requires a unique static source.

## Cycle detection

The graph explicitly detects provenance cycles. A cycle can arise from
recursion, an intentionally self-referential call topology, or inconsistent
composition inputs.

Cycles are retained and reported as:

```text
pointer-provenance-cycle
state = ambiguous
```

They are never silently collapsed into a root.

Use:

```bash
--fail-on-cycle
```

for workflows that require an acyclic chain.

## Heuristic vtable overlap

Any vtable-store overlap carried by the pointer-origin report remains an
`ambiguous` blocker in the closure graph:

```text
pointer_alias_proven = false
```

Graph reachability does not turn a same-register heuristic vtable STORE into a
proven vptr or class identity.

## Fail-closed policy

The composer refuses to:

- accept format drift;
- attach pointer-origin callsites absent from receiver provenance;
- invent a receiver register when the lower layer left it unknown;
- choose between conflicting static sources;
- collapse cycles into roots;
- infer owner/class identity from endpoints;
- infer aliasing from repeated register spelling;
- rename unknown fields or invent physical units.

## Next use

The resulting closure graph gives Process 1 one stable global view of pointer
provenance and one deduplicated next-target list.

The next semantic promotion should happen only when a completed provenance path
can be joined to an independent lifecycle fact for the **same pointer value**,
for example:

```text
proven allocation/global owner source
+ exact pointer-value chain
+ exact vtable STORE destination alias
+ reset/destructor use of the same pointer
```

Until those aliases are proven, lifecycle candidates stay ambiguous and the
closure remains a structural evidence graph rather than a recovered class
model.

No original-game execution or runtime capture is used.
