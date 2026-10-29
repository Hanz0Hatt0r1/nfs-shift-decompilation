#version 450

layout(set = 0, binding = 15, std140) uniform PixelConstants {
  vec4 c[256];
} pc;
layout(set = 1, binding = 0) uniform sampler2DMS source_image;
layout(location = 0) out vec4 color;

void main() {
  ivec2 position = ivec2(gl_FragCoord.xy * pc.c[0].xy);
  color = texelFetch(source_image, position, 0);
}
