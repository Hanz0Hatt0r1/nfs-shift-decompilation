#version 450

layout(location = 0) in vec3 in_position;

layout(push_constant) uniform Transform {
    vec4 center_scale;
} transform;

void main() {
    vec3 p = (in_position - transform.center_scale.xyz) * transform.center_scale.w;
    gl_Position = vec4(p, 1.0);
}
