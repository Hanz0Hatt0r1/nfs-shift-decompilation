# Shader backend status

Current pipeline:

D3D9 FXO -> register/operand parser -> `SHIFT.ShaderProgram/1` -> GLSL ES 3.1.

Implemented:
- neutral JSON shader IR;
- common arithmetic/vector operations;
- CMP/LRP;
- TEX/TEXLDD/TEXLDL;
- DSX/DSY;
- basic IFC/ELSE/ENDIF and bounded LOOP/REP lowering;
- regression tests against the real `glass.fxo` fixture.

Known limitations:
- exact relative constant addressing;
- D3D9 sampler state -> BMT/DDS state binding;
- semantic vertex/pixel interface linkage;
- exact loop-register semantics;
- compiler validation against a GLES compiler.

Next target: BMT + DDS + ShaderProgram -> material draw packet, then MGEO/VHF integration.
