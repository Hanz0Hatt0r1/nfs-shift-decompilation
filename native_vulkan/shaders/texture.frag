#version 450

layout(set = 1, binding = 1) uniform sampler2D tex1;
layout(location = 0) in vec2 v_uv;
layout(location = 0) out vec4 out_color;

void main() {
    out_color = texture(tex1, v_uv);
}
