#version 450

layout(set = 0, binding = 15, std140) uniform PixelConstants {
  vec4 c[256];
} pc;
layout(set = 1, binding = 0) uniform sampler2DMS source_image;
layout(location = 0) out uvec4 color;

void main() {
  ivec2 position = ivec2(gl_FragCoord.xy * pc.c[0].xy);
  vec4 average = (texelFetch(source_image, position, 0) +
                  texelFetch(source_image, position, 1) +
                  texelFetch(source_image, position, 2) +
                  texelFetch(source_image, position, 3)) * 0.25;
  vec4 scaled = clamp(average * 2048.0, vec4(0.0), vec4(65535.0));
  color = uvec4(floor(scaled + 0.5));
}
