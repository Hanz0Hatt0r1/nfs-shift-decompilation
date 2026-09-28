# Native submission provenance gate

## Contract

\`SHIFT.NativeSubmissionGate/1\` is stricter than the general
\`SHIFT.RenderCommand/1\` validator.

A native backend may consume a ready command only when every submesh carries:

- the SHA-256 of the complete source FXO payload;
- \`SHIFT.ShaderPermutationIdentity/1\`;
- a valid permutation identity SHA-256.

This prevents native execution from relying only on generated GLSL, shader IR,
or an ambiguous path lookup.

## Reproduction

\`python tools/validate_native_submission.py render_command.json -o native_gate.json\`

Exit code \`0\` means the command satisfies the provenance gate; \`2\` means it
is blocked.

The gate does not infer runtime equivalence and does not replace same-instance
D3D9 evidence.
