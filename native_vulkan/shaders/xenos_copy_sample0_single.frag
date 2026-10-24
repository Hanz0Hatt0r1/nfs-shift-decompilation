#version 450
layout(set=1,binding=0) uniform sampler2D source_image;
layout(location=0) out vec4 shift_color0;
void main() {
  vec4 c = texelFetch(source_image, ivec2(gl_FragCoord.xy), 0);
  c = floor(clamp(c, 0.0, 1.0) * 255.0 + 0.5) / 255.0;
  shift_color0 = c.bgra;
}
