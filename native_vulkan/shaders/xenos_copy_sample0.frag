#version 450

layout(set = 1, binding = 0) uniform sampler2DMS source_image;
layout(location = 0) out vec4 color;

void main() {
  vec4 source = texelFetch(source_image, ivec2(gl_FragCoord.xy), 0);
  source = floor(clamp(source, 0.0, 1.0) * 255.0 + 0.5) / 255.0;
  color = source.bgra;
}
