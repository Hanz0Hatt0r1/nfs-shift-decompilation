#version 450
layout(location = 0) in vec3 inPosition;
layout(location = 0) out vec3 outColor;

layout(push_constant) uniform PushConstants {
    mat4 mvp;
} pc;

void main() {
    gl_Position = pc.mvp * vec4(inPosition, 1.0);
    outColor = vec3(0.72, 0.76, 0.84);
}
