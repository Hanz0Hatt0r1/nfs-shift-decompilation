from __future__ import annotations
import re, struct
from dataclasses import dataclass, asdict
from pathlib import Path

VERSION_STAGE={0xFFFF:'pixel',0xFFFE:'vertex'}
@dataclass
class ShaderBlob:
    offset:int; end:int; stage:str; version:int; major:int; minor:int
    instruction_count:int; ctab_offset:int|None; ctab_size:int|None; ctab_strings:list[str]

def _ascii_strings(data,start,end,min_len=3):
    out=[]; i=max(0,start); end=min(end,len(data))
    while i<end:
        if 32<=data[i]<127:
            j=i+1
            while j<end and 32<=data[j]<127:j+=1
            if j-i>=min_len: out.append(data[i:j].decode('ascii','replace'))
            i=j
        else:i+=1
    return out

def _parse_ctab(data,payload,n):
    end=min(len(data),payload+n*4)
    if payload+32>end or data[payload:payload+4]!=b'CTAB':return None
    size,creator,version,constants,info,flags,target=struct.unpack_from('<7I',data,payload+4)
    # D3DXSHADER_CONSTANT_INFO is 20 bytes in the serialized CTAB:
    # name offset, register set/index/count, reserved, type-info offset,
    # default-value offset. Keep offsets as evidence and decode bounds-safely.
    constants_out=[]
    ci_end=min(end,payload+max(size,32)+constants*32+4096)
    for i in range(constants):
        off=payload+info+i*20
        if off+20>ci_end: break
        name_off, reg_set, reg_index, reg_count, reserved, type_off, default_off = struct.unpack_from('<IHHHHII',data,off)
        name=""
        if payload <= payload+name_off < ci_end:
            p=payload+name_off
            q=data.find(b'\\x00',p,ci_end)
            if q<0: q=ci_end
            name=data[p:q].decode('ascii','replace')
        type_info=None
        if payload <= payload+type_off < ci_end and payload+type_off+16<=ci_end:
            cls, typ, rows, cols, elements, members, member_info = struct.unpack_from('<BBHHHHI',data,payload+type_off)
            type_info={
                'class':cls,'type':typ,'rows':rows,'columns':cols,
                'elements':elements,'struct_members':members,
                'struct_member_info_offset':member_info,
            }
        constants_out.append({
            'index':i,'name':name,'register_set':reg_set,
            'register_index':reg_index,'register_count':reg_count,
            'type':type_info,'default_value_offset':default_off,
        })
    strings=_ascii_strings(data,payload,min(end,payload+max(size,32)+max(0,constants)*32+1024))
    return {
        'size':size,'creator_offset':creator,'version':version,
        'constant_count':constants,'constant_info_offset':info,
        'flags':flags,'target_offset':target,
        'constants':constants_out,'strings':strings,
    }


def parse_shader_blobs(data:bytes):
    out=[]; i=0
    while i+8<=len(data):
        v=struct.unpack_from('<I',data,i)[0]; hi=(v>>16)&0xffff
        if hi not in VERSION_STAGE or ((v>>8)&0xff) not in (2,3): i+=4; continue
        comment=struct.unpack_from('<I',data,i+4)[0]
        if (comment&0xffff)!=0xfffe: i+=4; continue
        n=comment>>16; payload=i+8
        if payload+4>len(data) or payload+n*4>len(data) or data[payload:payload+4]!=b'CTAB': i+=4; continue
        pos=payload+n*4; count=0; end=None
        while pos+4<=len(data):
            tok=struct.unpack_from('<I',data,pos)[0]
            if tok==0xffff:
                end=pos+4; break
            if (tok&0xffff)==0xfffe:
                ln=tok>>16
                if pos+4+ln*4>len(data):break
                pos+=4+ln*4; continue
            ln=(tok>>24)&0x0f
            # D3D9 stores the number of parameter tokens in the instruction-length field.
            step=(1+ln)*4 if ln else 4
            if pos+step>len(data):break
            count+=1; pos+=step
        if end is None:i+=4;continue
        ctab=_parse_ctab(data,payload,n)
        out.append(ShaderBlob(i,end,VERSION_STAGE[hi],v,(v>>8)&255,v&255,count,payload,ctab['size'] if ctab else None,ctab['strings'] if ctab else []))
        i=end
    return out

def parse_fx_source(src:bytes):
    text=src.decode('utf-8','replace')
    includes=sorted(set(re.findall(r'#\s*include\s*["<]([^">]+)[">]',text)))
    defines=sorted(set(re.findall(r'^\s*#\s*define\s+([A-Za-z_]\w*)',text,re.M)))
    techniques=re.findall(r'\btechnique(?:10)?\s+([A-Za-z_]\w*)\s*\{',text)
    passes=re.findall(r'\bpass\s+([A-Za-z_]\w*)\s*\{',text)
    params=[]
    pat=re.compile(r'^\s*(?:SHARE_PARAM\s+)?(float(?:[1-4](?:x[1-4])?)?|half(?:[1-4](?:x[1-4])?)?|int(?:[1-4])?|bool(?:[1-4])?|sampler\w*|Texture\w*)\s+([A-Za-z_]\w*)\s*(?::\s*([A-Za-z_]\w*))?',re.M|re.I)
    for m in pat.finditer(text):params.append({'type':m.group(1),'name':m.group(2),'semantic':m.group(3)})
    return {'includes':includes,'defines':defines,'techniques':techniques,'passes':passes,'parameters':params}
