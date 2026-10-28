#version 450

layout(set = 1, binding = 0) uniform sampler2DMS source_image;
layout(location = 0) out vec4 color;

void main() {
  ivec2 dst = ivec2(gl_FragCoord.xy);
  int tile_x = dst.x / 80;
  int tile_y = dst.y / 16;
  int local_x = dst.x % 80;
  int local_y = dst.y % 16;
  ivec2 src = ivec2(tile_x * 40 + local_x / 2,
                    tile_y * 8 + local_y / 2);
  int sample_index = (local_y % 2) * 2 + (local_x % 2);
  vec4 value = texelFetch(source_image, src, sample_index);
  color = floor(clamp(value, 0.0, 1.0) * 255.0 + 0.5) / 255.0;
}
