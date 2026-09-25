#version 450

layout(set = 1, binding = 3) uniform samplerCube tex3;
layout(location = 0) in vec3 v_direction;
layout(location = 0) out vec4 out_color;

void main() {
    out_color = texture(tex3, normalize(v_direction));
}
