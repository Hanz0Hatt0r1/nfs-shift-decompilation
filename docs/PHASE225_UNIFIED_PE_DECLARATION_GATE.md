# Phase 225 — unified D3D9 declaration gate

Phase 225 composes the existing SHIFT.D3D9DeclarationChainEvidence/1 with the exact SHIFT.exe PE semantic map. The gate can optionally consume a runtime declaration instance and run SHIFT.D3D9RuntimePESemanticParity/1.

The gate deliberately keeps the final same-instance MEB-resource-to-DrawIndexedPrimitive proof separate. It only establishes that static declaration semantics and any supplied runtime numeric Type/Usage fields agree with the exact executable ABI.
