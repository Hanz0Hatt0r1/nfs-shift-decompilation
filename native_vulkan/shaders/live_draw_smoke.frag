#version 450
layout(location = 0) in vec2 uv;
layout(location = 0) out vec4 color;
layout(set = 0, binding = 15, std140) uniform PixelConstants {
  vec4 c[256];
} pixel_constants;
layout(set = 1, binding = 0) uniform sampler2D source_texture;

void main() {
  color = texture(source_texture, uv);
}
