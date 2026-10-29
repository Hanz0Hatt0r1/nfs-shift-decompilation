#version 450

layout(set = 0, binding = 15, std140) uniform PixelConstants {
  vec4 c[256];
} pc;
layout(set = 1, binding = 0) uniform sampler2DMS source_image;
layout(location = 0) out vec4 color;

vec3 linear_to_xenos_gamma(vec3 linear_rgb) {
  linear_rgb = clamp(linear_rgb, 0.0, 1.0);
  vec3 gamma_scale = mix(vec3(1023.0), vec3(1023.0 / 2.0),
                         step(vec3(64.0 / 1023.0), linear_rgb));
  gamma_scale = mix(gamma_scale, vec3(1023.0 / 4.0),
                    step(vec3(128.0 / 1023.0), linear_rgb));
  gamma_scale = mix(gamma_scale, vec3(1023.0 / 8.0),
                    step(vec3(512.0 / 1023.0), linear_rgb));
  vec3 gamma_offset = mix(vec3(0.0), vec3(32.0),
                          step(vec3(64.0 / 1023.0), linear_rgb));
  gamma_offset = mix(gamma_offset, vec3(64.0),
                     step(vec3(128.0 / 1023.0), linear_rgb));
  gamma_offset = mix(gamma_offset, vec3(128.0),
                     step(vec3(512.0 / 1023.0), linear_rgb));
  return (trunc(linear_rgb * gamma_scale) + gamma_offset) / 255.0;
}

void main() {
  ivec2 p = ivec2(gl_FragCoord.xy * pc.c[0].xy);
  vec4 source = texelFetch(source_image, p, 0);
  source.rgb = linear_to_xenos_gamma(source.rgb);
  color = floor(clamp(source, 0.0, 1.0) * 255.0 + 0.5) / 255.0;
}
