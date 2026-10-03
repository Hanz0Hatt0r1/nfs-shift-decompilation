# Ghidra subsystem method-name cross-check

`tools/ghidra/join_method_anchors_to_subsystems.py` composes two existing static evidence layers without converting either one into stronger semantics on its own:

1. `SHIFT.GhidraMethodNameAnchors/1` exact `MWL::...::Method` string anchors;
2. `SHIFT.GhidraSubsystemManifestIndex/1` subsystem aliases, AI registrations and their one-hop direct-call slices.

The output format is `SHIFT.GhidraSubsystemMethodAnchors/1`.

## Promotion rule

A method-name row becomes a `subsystem-crosschecked-method-name-candidate` only when all of the following are true:

- the Ghidra function contains exactly one distinct conservative method-name anchor;
- that exact method name matches one narrow subsystem prefix rule;
- the same function address is already present in that subsystem's independently established one-hop evidence slice.

The current rules intentionally cover only narrow, reviewable prefixes:

- renderer: `MWL::Renderer::`;
- physics: `MWL::Physics::`, `MWL::Core::Physics...`, `MWL::Core::cPhysics...`, `MWL::Core::LoadCollision...`;
- vehicle: `MWL::Vehicle::`, `MWL::Core::Vehicle...`;
- scene graph: `MWL::GraphicsEngine::CSceneGraph::`;
- AI: `MWL::AI::`.

A broad prefix such as `MWL::Core::` is deliberately **not** assigned to a subsystem.

## Non-promoted states

The report keeps several useful observations separate:

- `namespace-only-method-name-candidate`: the exact name looks subsystem-specific, but the function is not in that subsystem slice yet;
- `slice-only-unclassified-method-name-candidate`: the function is in a subsystem slice, but the exact name has no narrow namespace rule;
- `unclassified-method-name-candidate`: neither independent signal is sufficient;
- `ambiguous-method-name-anchors`: one function contains multiple distinct method-name strings and is never promoted by this layer.

This distinction is important for functions which contain several assert/debug strings naming nearby methods. A function such as a dispatcher or shared validation path must not acquire one arbitrary method name merely because one string is present.

## Run

```bash
python3 tools/ghidra/join_method_anchors_to_subsystems.py \
  out/shift_ghidra_database \
  --json-out out/ghidra_subsystem_method_anchors.json
```

The command rebuilds both source evidence layers from the same Ghidra export before joining them, so address identity cannot silently drift between exports.

## Evidence boundary

A promoted row is still a **semantic-name candidate**, not an in-place rename and not proof of the complete C++ method contract. This layer does not prove:

- full method behavior;
- parameter meaning or ABI beyond separately established evidence;
- virtual-table slot identity;
- class ownership/lifetime policy;
- that every instruction in the containing Ghidra function belongs to the named source-level method.

Those claims require additional call-shape, instruction, layout, runtime or independent source evidence.
