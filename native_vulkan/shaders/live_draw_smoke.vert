#version 450
layout(location = 0) out vec4 uv;
layout(set = 0, binding = 14, std140) uniform VertexConstants {
  vec4 c[256];
} vertex_constants;

void main() {
  const vec2 positions[3] = vec2[3](vec2(-0.5, 0.0), vec2(0.0, 0.5),
                                   vec2(0.5, -0.5));
  gl_Position = vec4(positions[gl_VertexIndex], 0.0, 1.0);
  gl_PointSize = 1.0;
  uv = vec4(0.5, 0.5, 0.0, 1.0);
}
