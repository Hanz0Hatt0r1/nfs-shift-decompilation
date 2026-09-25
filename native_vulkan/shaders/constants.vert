#version 450

layout(set = 0, binding = 14, std140) uniform ShiftVertexConstants {
    vec4 c[256];
} vertex_constants;

void main() {
    const vec2 positions[3] = vec2[3](
        vec2(0.0, -0.7),
        vec2(0.7, 0.7),
        vec2(-0.7, 0.7)
    );
    vec2 offset = vertex_constants.c[0].xy;
    gl_Position = vec4(positions[gl_VertexIndex] + offset, 0.0, 1.0);
}
