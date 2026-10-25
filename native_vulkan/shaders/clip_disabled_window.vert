#version 450
layout(location = 0) out vec4 uv;

void main() {
  const vec2 window_positions[3] = vec2[3](
      vec2(0.0, 0.0), vec2(1280.0, 0.0), vec2(0.0, 720.0));
  const vec2 texture_coordinates[3] = vec2[3](
      vec2(0.0, 0.0), vec2(1.0, 0.0), vec2(0.0, 1.0));
  vec2 p = window_positions[gl_VertexIndex];
  gl_Position = vec4(p * vec2(2.0 / 1280.0, 2.0 / 720.0) - 1.0,
                     0.0, 1.0);
  uv = vec4(texture_coordinates[gl_VertexIndex], 0.0, 1.0);
}
