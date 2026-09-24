# Phase 117 — updated implementation plan

Phase 116 established the supplied 1.02 corpus bridge for COLOR0:
MEB 460 -> [4,6,0], with Type 4 identified as D3DCOLOR. The next blocker is no
longer corpus extraction; it is a same-instance runtime declaration correlation.

## Implemented in Phase 117

- SHIFT.D3D9RuntimeBindingEvidence/1 consumes external JSONL D3D9 capture events.
- Declaration creation bytes are decoded through the existing declaration-instance contract.
- SetVertexDeclaration, stream source, index binding and draw events are grouped per frame.
- MEB resource identity can be matched by SHA-256 or normalized path.
- MEB descriptor matching requires an explicit Usage-ordinal map; no Usage byte is guessed.
- SHIFT.BMWGoldenAssetManifest/1 selects a real BMW M3 E36 1.02 MEB resource and
  records stable identity, geometry, material references and the proven COLOR0 descriptor.
- Project-local skills now encode the Ghidra, D3D9, shader and BMW golden workflows.

## Acceptance gate

The runtime bridge is considered proven only when one capture supplies:

1. a decoded declaration instance;
2. the same declaration pointer passed to SetVertexDeclaration;
3. the same MEB resource identity;
4. an evidence-backed Usage ordinal → D3D9 Usage byte mapping;
5. a declaration record matching the MEB [Type,UsageOrdinal,Channel] triple.

## Next vertical slice

After the runtime bridge, continue with:

BMW golden MEB -> material/linker -> unique FXO pair -> RenderCommand -> desktop golden image

Capture-derived declaration/type evidence must be joined before changing the vertex ABI
from inferred to proven. The raw BMW BFF remains external and is not committed.