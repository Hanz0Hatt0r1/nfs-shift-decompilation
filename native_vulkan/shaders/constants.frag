#version 450

layout(set = 0, binding = 15, std140) uniform ShiftPixelConstants {
    vec4 c[256];
} pixel_constants;

layout(location = 0) out vec4 out_color;

void main() {
    out_color = pixel_constants.c[0];
}
