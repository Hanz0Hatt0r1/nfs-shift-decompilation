#version 450

layout(location = 0) out vec4 color;

void main() {
  int lane = (int(gl_FragCoord.y) & 1) * 2 + (int(gl_FragCoord.x) & 1);
  color = vec4(0.125 + 0.25 * float(lane), 0.0, 0.0, 1.0);
}
