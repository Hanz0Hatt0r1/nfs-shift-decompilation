#version 450
layout(location = 0) in vec3 position;
layout(location = 0) out vec2 uv;
layout(set = 0, binding = 14, std140) uniform VertexConstants {
  vec4 c[256];
} vertex_constants;

void main() {
  gl_Position = vec4(position, 1.0);
  uv = vec2(0.5);
}
