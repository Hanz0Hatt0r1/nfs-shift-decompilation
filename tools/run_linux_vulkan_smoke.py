#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
from bmw_vulkan_bundle import TARGET_MEB, build_bmw_vulkan_bundle
from vulkan_bundle_run import run_bmw_vulkan_bundle

VERTEX_GLSL = """#version 450
layout(location=0) in vec3 position;
layout(location=0) out vec2 v_uv;
layout(location=1) out vec3 v_dir;
layout(set=0,binding=14,std140) uniform ShiftVertexConstants { vec4 c[256]; } vertex_constants;
void main() {
  const vec2 uv[3]=vec2[3](vec2(0.0),vec2(1.0,0.0),vec2(0.5,1.0));
  const vec3 dir[3]=vec3[3](vec3(-1,0,1),vec3(1,0,1),vec3(0,1,1));
  gl_Position=vec4(position+vertex_constants.c[0].xyz,1.0);
  v_uv=uv[gl_VertexIndex]; v_dir=dir[gl_VertexIndex];
}"""
PIXEL_GLSL = """#version 450
layout(location=0) in vec2 v_uv;
layout(location=1) in vec3 v_dir;
layout(location=0) out vec4 out_color;
layout(set=0,binding=15,std140) uniform ShiftPixelConstants { vec4 c[256]; } pixel_constants;
layout(set=1,binding=1) uniform sampler2D tex1;
layout(set=1,binding=3) uniform samplerCube tex3;
void main(){out_color=texture(tex1,v_uv)*texture(tex3,normalize(v_dir))*pixel_constants.c[1];}"""

def command():
  return {"format":"SHIFT.RenderCommand/1","ready":True,"blocking_reasons":[],"mesh":{
    "ref":TARGET_MEB,"resolved":{"resource_sha256":"960ac728db8dc1e870ae348cf77fa3a18feb1a359bc6f31a865b528b931b2c2c"},
    "vertex_count":3,"triangle_count":1,"vertex_layout":{"format":"SHIFT.VertexLayout/1","buffer_stride":12,
    "attributes":[{"property_id":"200","usage":"POSITION","usage_index":0,"location":0,"offset":0,"stride":12,
    "storage":"FLOAT32x3","android":"FLOAT32x3","components":3,"normalized":False,"element_size":12,"abi_status":"proven"}]}},
    "submeshes":[{"shader":{"vulkan_vertex_glsl":VERTEX_GLSL,"vulkan_pixel_glsl":PIXEL_GLSL},
    "constant_commands":[{"name":"ObjectOffset","stage":"vertex","register_index":0,"register_count":1},{"name":"Tint","stage":"pixel","register_index":1,"register_count":1}],
    "constant_payload":{"format":"SHIFT.MaterialConstantPayload/1","ready":True,"registers":[
      {"register_index":0,"values":[0,0,0,0]},{"register_index":1,"values":[1,1,1,1]}]},
    "textures":[{"sampler":"diffuseMap","d3d9_sampler_register":1,"resource_binding_id":1,"texture_id":1,"sampler_id":1,
      "sampler_state":{"format":"SHIFT.SamplerState/1","min_filter":"LINEAR","mag_filter":"LINEAR","address_u":"REPEAT","address_v":"REPEAT"}}],
    "external_samplers":[{"sampler":"environmentMap","sampler_type":"samplerCube","d3d9_sampler_register":3,
      "sampler_state":{"min_filter":"LINEAR","mag_filter":"LINEAR","address_u":"CLAMP_TO_EDGE","address_v":"CLAMP_TO_EDGE","address_w":"CLAMP_TO_EDGE"}}],
    "first_index":0,"index_count":3}]}}

def main():
  p=argparse.ArgumentParser(); p.add_argument("output_dir"); p.add_argument("--executable",default="native_vulkan/build/shift_vulkan_bundle_execute"); p.add_argument("--validator",default="glslangValidator"); a=p.parse_args()
  root=Path(a.output_dir); bundle_dir=root/"bundle"; root.mkdir(parents=True,exist_ok=True)
  mesh={"format":"SHIFT.MEB","vertices":[[-.65,-.55,0],[.65,-.55,0],[0,.65,0]],"indices":[0,1,2]}
  tex={"format":"SHIFT.ReferenceTexture/1","width":1,"height":1,"pixel_format":"RGBA8","pixels":[255,96,96,255]}
  cube={"format":"SHIFT.ReferenceCubeTexture/1","faces":{f:{"format":"SHIFT.ReferenceTexture/1","width":1,"height":1,"pixel_format":"RGBA8","pixels":[96,255,96,255]} for f in ("px","nx","py","ny","pz","nz")}}
  build_bmw_vulkan_bundle({"format":"SHIFT.RenderBinding/1","render_commands":[command()]},mesh,bundle_dir,textures={"1":tex},environment_cube=cube)
  result=run_bmw_vulkan_bundle(bundle_dir,executable=a.executable,validator=a.validator,output=bundle_dir/"bundle.ppm")
  (root/"smoke_result.json").write_text(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
  if result["status"]!="rendered": raise SystemExit(2)
  output=Path(result["native"]["output"])
  if output.read_bytes()[:2]!=b"P6": raise SystemExit("not a PPM")
  print(json.dumps({"format":result["format"],"status":result["status"],"output":str(output),"output_bytes":output.stat().st_size},ensure_ascii=False,indent=2))

if __name__=="__main__": main()
