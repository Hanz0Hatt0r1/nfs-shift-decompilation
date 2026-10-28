#version 450

layout(set = 0, binding = 15, std140) uniform PixelConstants {
  vec4 c[256];
} pixel_constants;
layout(location = 0) out vec4 color;

void main() {
  int lane = clamp(int(pixel_constants.c[0].x + 0.5), 0, 3);
  color = vec4(0.125 + 0.25 * float(lane), 0.0, 0.0, 1.0);
  gl_SampleMask[0] = 1 << lane;
}
