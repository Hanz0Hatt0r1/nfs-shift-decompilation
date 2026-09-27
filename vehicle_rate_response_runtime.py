"""Exact numeric reconstruction of FUN_0075ada0/FUN_007595d0/FUN_007682c0."""
from __future__ import annotations
from dataclasses import dataclass
from math import isfinite, sqrt

FORMAT="SHIFT.VehicleRateResponseRuntime/1"
SOURCE_FILE="SHIFT.exe.c"
GEOMETRY_LINE=754456
RESPONSE_LINE=753509
APPLY_LINE=760210
FLT_MAX=3.4028235e38

@dataclass(frozen=True)
class Vec3:
    x: float
    y: float
    z: float
    def __post_init__(self):
        if not all(isfinite(float(v)) for v in (self.x,self.y,self.z)):
            raise ValueError("vector components must be finite")
    def as_tuple(self): return (float(self.x),float(self.y),float(self.z))

def _cross(a:Vec3,b:Vec3)->Vec3:
    return Vec3(a.y*b.z-a.z*b.y,a.z*b.x-a.x*b.z,a.x*b.y-a.y*b.x)
def _clamp(v:float,lo:float,hi:float)->float:
    return min(hi,max(lo,v))
def _sign(v:float)->float:
    return 1.0 if v>0.0 else -1.0 if v<0.0 else 0.0

@dataclass(frozen=True)
class RateGeometryResult:
    speed: float
    direction: Vec3
    lateral_direction: Vec3
    radius_like: float
    reciprocal_like: float
    valid: bool

def rate_geometry(speed_x:float,speed_z:float,lateral_x:float,lateral_z:float)->RateGeometryResult:
    speed=sqrt(speed_x*speed_x+speed_z*speed_z)
    if speed < 4.0:
        return RateGeometryResult(speed,Vec3(0,0,0),Vec3(0,0,0),0.0,0.0,False)
    direction=Vec3(speed_x/speed,0.0,speed_z/speed)
    lateral=_cross(direction,Vec3(0.0,1.0,0.0))
    projection=lateral.x*lateral_x+lateral.z*lateral_z
    if abs(projection)<0.001:
        return RateGeometryResult(speed,direction,lateral,FLT_MAX,0.0,True)
    radius_like=(speed*speed)/projection
    reciprocal_like=-speed/radius_like
    return RateGeometryResult(speed,direction,lateral,radius_like,reciprocal_like,True)

def response_595d0(body_y:float, steering:float, angle_limit:float, speed_factor:float,
                   full_scale:float, response_angle:float, response_scale:float,
                   reciprocal:float, field_4054:float, field_0120:float)->float:
    f3=body_y-reciprocal
    f6=abs(steering)-angle_limit
    if f6<0.0:
        return 0.0
    f6=min(response_angle,f6)
    sign=_sign(steering)
    f5=field_4054*0.5*field_0120*9.81*1.3
    f8=(-sign)*f3
    p8=min(1.0,f6/response_angle)*0.3 if f8>=0.0 else 5.0
    out=f5*(p8*response_scale)*(-speed_factor)*f8 + f5*(-speed_factor)*full_scale*f6
    return (-sign*out) if out<0.0 else 0.0

def apply_682c0(speed3d:float, steering:float, scale:float, response_gear:float,
                body_y:float, velocity_x:float, velocity_y:float, velocity_z:float,
                lateral_x:float, lateral_z:float, field_4054:float, field_0120:float,
                global_angle_mode:int)->float:
    if speed3d < 5.0:
        return 0.0
    speed_factor=_clamp((speed3d-5.0)/15.0,0.0,1.0)
    geom=rate_geometry(velocity_x,velocity_z,lateral_x,lateral_z)
    reciprocal=geom.reciprocal_like if geom.valid else 0.0
    angle_limit=0.95993114 if global_angle_mode>=2 else 0.69813174
    response=response_595d0(body_y,steering,angle_limit,speed_factor,1.0,0.5235988,1.0,
                            reciprocal,field_4054,field_0120)
    return response*scale*response_gear

def build_contract():
    return {
        "format":FORMAT,"version":1,
        "source":{"file":SOURCE_FILE,"geometry_line":GEOMETRY_LINE,
                  "response_line":RESPONSE_LINE,"apply_line":APPLY_LINE},
        "geometry":{
            "function":"FUN_0075ada0","input_speed":"body +0x78/+0x88",
            "speed":"sqrt(vx^2 + vz^2)","minimum_speed":4.0,
            "direction":"(vx/speed, 0, vz/speed)",
            "lateral_direction":"direction x (0,1,0)",
            "projection":"lateral.x * field+0x4084 + lateral.z * field+0x408c",
            "near_zero_projection":"abs(projection) < 0.001 => radius=FLT_MAX, reciprocal=0",
            "radius":"speed^2 / projection","reciprocal":"-speed / radius"},
        "response":{
            "function":"FUN_007595d0",
            "angle_limits":{"mode_lt_2":0.69813174,"mode_ge_2":0.95993114},
            "response_angle":0.5235988,
            "base":"field+0x4054 * 0.5 * body+0x120 * 9.81 * 1.3",
            "angle_delta":"clamp(abs(steering)-angle_limit, 0, 0.5235988)",
        },
        "apply":{
            "function":"FUN_007682c0","speed_gate":"speed >= 5",
            "speed_factor":"clamp((speed-5)/15,0,1)",
            "accumulator_offsets":["body +0x48 += 0","body +0x50 += result","body +0x58 += 0"]},
        "status":"machine-code-backed arithmetic; physical field names remain unnamed",
    }

__all__=["FORMAT","Vec3","RateGeometryResult","rate_geometry","response_595d0","apply_682c0",
         "build_contract","FLT_MAX"]
