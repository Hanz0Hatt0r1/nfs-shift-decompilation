#version 450
layout(location = 0) in vec4 uv;
layout(location = 0) out vec4 color;

void main() {
  color = vec4(uv.xy, 0.0, 1.0);
}
