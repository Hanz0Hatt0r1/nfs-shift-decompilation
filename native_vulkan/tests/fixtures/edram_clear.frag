#version 450

layout(location = 0) out vec4 color;

void main() {
  color = vec4(0.0);
  gl_FragDepth = 1.0;
}
