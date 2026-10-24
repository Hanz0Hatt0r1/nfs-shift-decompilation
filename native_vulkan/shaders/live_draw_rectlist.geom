#version 450
layout(triangles) in;
layout(triangle_strip, max_vertices=4) out;
layout(location=0) in vec4 uv_in[];
layout(location=0) out vec4 uv;

void main() {
  vec2 p0 = gl_in[0].gl_Position.xy;
  vec2 p1 = gl_in[1].gl_Position.xy;
  vec2 p2 = gl_in[2].gl_Position.xy;
  float d01 = dot(p1 - p0, p1 - p0);
  float d12 = dot(p2 - p1, p2 - p1);
  float d20 = dot(p0 - p2, p0 - p2);
  int a;
  int b;
  int c;
  if (d12 > d20 && d12 > d01) {
    a = 0; b = 1; c = 2;
  } else if (d20 > d01) {
    a = 1; b = 2; c = 0;
  } else {
    a = 2; b = 0; c = 1;
  }
  for (int i = 0; i < 3; ++i) {
    int v = i == 0 ? a : (i == 1 ? b : c);
    gl_Position = gl_in[v].gl_Position;
    uv = uv_in[v];
    EmitVertex();
  }
  gl_Position = -gl_in[a].gl_Position + gl_in[b].gl_Position + gl_in[c].gl_Position;
  uv = -uv_in[a] + uv_in[b] + uv_in[c];
  EmitVertex();
  EndPrimitive();
}
