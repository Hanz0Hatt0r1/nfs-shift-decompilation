from __future__ import annotations
import struct, math
from dataclasses import dataclass, asdict, field
from typing import Optional

# D3DSIO values used by the SHIFT shader cache. Values are the standard D3D9
# instruction opcode numbers; unknown values remain numeric instead of being dropped.
OPCODES = {
  0:'NOP',1:'MOV',2:'ADD',3:'SUB',4:'MAD',5:'MUL',6:'RCP',7:'RSQ',8:'DP3',9:'DP4',
  10:'MIN',11:'MAX',12:'SLT',13:'SGE',14:'EXP',15:'LOG',16:'LIT',17:'DST',18:'LRP',
  19:'FRC',20:'M4x4',21:'M4x3',22:'M3x4',23:'M3x3',24:'M3x2',25:'CALL',26:'CALLNZ',
  27:'LOOP',28:'RET',29:'ENDLOOP',30:'LABEL',31:'DCL',32:'POW',33:'CRS',34:'SGN',
  35:'ABS',36:'NRM',37:'SINCOS',38:'REP',39:'ENDREP',40:'IF',41:'IFC',42:'ELSE',43:'ENDIF',
  44:'BREAK',45:'BREAKC',46:'MOVA',47:'DEFB',48:'DEFI',49:'TEXCOORD',50:'TEXKILL',
  51:'TEX',52:'TEXBEM',53:'TEXBEML',54:'TEXREG2AR',55:'TEXREG2GB',56:'TEXM3x2PAD',
  57:'TEXM3x2TEX',58:'TEXM3x3PAD',59:'TEXM3x3TEX',60:'TEXM3x3SPEC',61:'TEXM3x3VSPEC',
  62:'EXPP',63:'LOGP',64:'CND',65:'DEF',66:'TEX',67:'TEXDP3TEX',68:'TEXM3x2DEPTH',
  69:'TEXDP3',70:'TEXM3x3',71:'TEXDEPTH',72:'CMP',73:'BEM',74:'DP2ADD',75:'DSX',
  76:'DSY',77:'TEXLDD',78:'SETP',79:'TEXLDL',80:'BREAKP',81:'DEF',82:'DEFI',83:'DEFB',
  84:'DDX',85:'DDY',86:'SAMPLE',87:'SAMPLE_C',88:'CMP',89:'BEM',90:'DP2ADD',91:'DSX',92:'DSY',93:'TEXLDD',94:'SETP',95:'TEXLDL',96:'BREAKP'
}
# The cache observed in SHIFT uses the standard D3DSIO numbering for the common
# SM2/SM3 opcodes (e.g. MOV=1, ADD=2, MAD=4, TEX=66, CMP=88, TEXLDD=93).

REG_TYPES = {
  0:'temp',1:'input',2:'const',3:'addr_or_texture',4:'rastout',5:'attrout',6:'texcoordout_or_output',
  7:'constint',8:'colorout',9:'depthout',10:'sampler',11:'const2',12:'const3',13:'const4',
  14:'constbool',15:'loop',16:'tempfloat16',17:'misctype',18:'label',19:'predicate'
}
SRC_MODS = {0:'',1:'-',2:'bias',3:'biasneg',4:'sign',5:'signneg',6:'comp',7:'x2',8:'x2neg',9:'dz',10:'dw',11:'abs',12:'absneg',13:'not'}
COMP='xyzw'
SEMANTICS={0:'POSITION',1:'BLENDWEIGHT',2:'BLENDINDICES',3:'NORMAL',4:'PSIZE',5:'TEXCOORD',6:'POSITIONT',7:'COLOR',8:'FOG',9:'DEPTH',10:'SAMPLE'}

@dataclass
class Operand:
    token:int
    kind:str='literal'
    reg_type:Optional[int]=None
    reg_name:Optional[str]=None
    index:Optional[int]=None
    swizzle:Optional[str]=None
    source_modifier:Optional[int]=None
    write_mask:Optional[str]=None
    result_modifier:Optional[int]=None
    relative:bool=False
    relative_token:Optional[int]=None
    value:Optional[object]=None
    text:Optional[str]=None

    def to_dict(self): return asdict(self)

@dataclass
class Instruction:
    offset:int
    opcode:int
    name:str
    token:int
    length:int
    controls:int
    predicated:bool
    operands:list[Operand]=field(default_factory=list)

@dataclass
class ShaderProgram:
    offset:int
    end:int
    stage:str
    major:int
    minor:int
    instructions:list[Instruction]
    inputs:list[dict]
    outputs:list[dict]
    samplers:list[int]
    constants:list[int]
    temps:list[int]
    unsupported_opcodes:list[int]


def reg_type(tok:int)->int:
    return ((tok>>28)&7) | ((tok>>8)&0x18)

def is_param_token(tok:int)->bool:
    return bool(tok & 0x80000000)

def swizzle_str(sw:int)->str:
    s=''.join(COMP[(sw>>(2*i))&3] for i in range(4))
    if s in ('xxxx','yyyy','zzzz','wwww'): return s[0]
    return s

def decode_source(tok:int)->Operand:
    rt=reg_type(tok); idx=tok&0x7ff; sw=(tok>>16)&0xff; mod=(tok>>24)&0xf
    return Operand(token=tok,kind='source',reg_type=rt,reg_name=REG_TYPES.get(rt,f'reg{rt}'),index=idx,
                   swizzle=swizzle_str(sw),source_modifier=mod,relative=bool(tok&(1<<13)),
                   text=render_operand(tok,False))

def decode_dest(tok:int)->Operand:
    rt=reg_type(tok); idx=tok&0x7ff; mask=(tok>>16)&0xf; rm=(tok>>20)&0xf
    wm=''.join(COMP[i] for i in range(4) if mask&(1<<i)) or 'xyzw'
    return Operand(token=tok,kind='dest',reg_type=rt,reg_name=REG_TYPES.get(rt,f'reg{rt}'),index=idx,
                   write_mask=wm,result_modifier=rm,relative=bool(tok&(1<<13)),text=render_operand(tok,True))

def decode_literal(tok:int)->Operand:
    return Operand(token=tok,kind='literal',value=struct.unpack('<f',struct.pack('<I',tok))[0],text=f'0x{tok:08x}')

def decode_token(tok:int, dest=False)->Operand:
    return decode_dest(tok) if dest and is_param_token(tok) else decode_source(tok) if is_param_token(tok) else decode_literal(tok)

def render_operand(tok:int,dest:bool)->str:
    rt=reg_type(tok); idx=tok&0x7ff
    names={0:'r',1:'v',2:'c',3:'a',4:'oR',5:'oD',6:'oT',7:'i',8:'oC',9:'oDepth',10:'s',11:'c2',12:'c3',13:'c4',14:'b',15:'aL',16:'h',17:'misc',18:'l',19:'p'}
    base=names.get(rt,f'reg{rt}')+str(idx)
    if dest:
        m=(tok>>16)&0xf
        if m and m!=15: base+='.'+''.join(COMP[i] for i in range(4) if m&(1<<i))
        return base
    sw=swizzle_str((tok>>16)&0xff)
    if sw!='xyzw': base+='.'+sw
    mod=(tok>>24)&0xf
    if mod==1:return '-'+base
    if mod==6:return '(1-'+base+')'
    if mod==11:return 'abs('+base+')'
    if mod==12:return '-abs('+base+')'
    return base

def _literal_for_dcl(tok:int):
    usage=tok&0xf; idx=(tok>>16)&0xf
    return {'usage':SEMANTICS.get(usage,f'USAGE{usage}'),'usage_code':usage,'index':idx,'token':tok}

def parse_program(data:bytes, blob_offset:int=0, blob_end:int|None=None, stage:str='unknown', major:int=3, minor:int=0)->ShaderProgram:
    end=len(data) if blob_end is None else blob_end
    pos=blob_offset
    version=struct.unpack_from('<I',data,pos)[0]
    if (version>>16)==0xffff: stage='pixel'
    elif (version>>16)==0xfffe: stage='vertex'
    major=(version>>8)&0xff; minor=version&0xff; pos+=4
    ins=[]; inputs=[]; outputs=[]; samplers=set(); consts=set(); temps=set(); unsupported=set()
    while pos+4<=end:
        tok=struct.unpack_from('<I',data,pos)[0]; op=tok&0xffff
        if op==0xffff: pos+=4; break
        if op==0xfffe:
            n=tok>>16; pos+=4+n*4; continue
        ln=(tok>>24)&0xf; pred=bool(tok&(1<<28)); count=ln
        raw=[]
        p=pos+4
        consumed=0
        while consumed<count and p+4<=end:
            t=struct.unpack_from('<I',data,p)[0]; p+=4; raw.append(t); consumed+=1
            # Relative-address token is itself included in the instruction length.
        # Length counts the extra relative token too; p should agree with the declared size.
        declared_end=pos+(1+ln)*4
        if declared_end> end: break
        operands=[]
        # Destination is first parameter for normal arithmetic instructions. DCL/DEF are special.
        if op==31 and len(raw)>=2:
            # D3D9 DCL is: semantic token, destination/register token. Both are DWORDs.
            sem=_literal_for_dcl(raw[0]); d=decode_dest(raw[1])
            operands.append(Operand(token=raw[0],kind='declaration',value=sem,text=f"{sem['usage']}{sem['index']}"))
            operands.append(d)
            sem['register']=d.text
            if d.reg_type in (1,): inputs.append(sem)
            elif d.reg_type in (6,): outputs.append(sem)
            elif d.reg_type in (8,9): outputs.append(sem)
        elif raw:
            # Literal-only DEF/DEFI/DEFB have a register destination followed by literals.
            operands.append(decode_dest(raw[0]) if is_param_token(raw[0]) else decode_literal(raw[0]))
            for t in raw[1:]: operands.append(decode_source(t) if is_param_token(t) else decode_literal(t))
        for x in operands:
            if x.reg_type==10: samplers.add(x.index)
            if x.reg_type in (2,11,12,13): consts.add(x.index)
            if x.reg_type in (0,16): temps.add(x.index)
        name=OPCODES.get(op,f'OP_{op}')
        if name.startswith('OP_'): unsupported.add(op)
        ins.append(Instruction(pos,op,name,tok,ln,(tok>>16)&0xff,pred,operands))
        pos=declared_end
    return ShaderProgram(blob_offset,pos,stage,major,minor,ins,inputs,outputs,sorted(samplers),sorted(consts),sorted(temps),sorted(unsupported))


def _glsl_reg(o:Operand, stage:str)->str:
    rt=o.reg_type; idx=o.index or 0
    if rt==0: base=f'r{idx}'
    elif rt==1: base=f'in_{idx}'
    elif rt==2: base=f'c[{idx}]'
    elif rt in (11,12,13): base=f'c[{idx}]'
    elif rt==3: base=f'a{idx}' if stage=='vertex' else f'tex{idx}'
    elif rt==6: base=f'out_{idx}'
    elif rt==8: base=f'fragColor{idx}'
    elif rt==9: base='gl_FragDepth'
    elif rt==10: base=f'tex{idx}'
    elif rt==17: base=f'misc{idx}'
    elif rt==19: base='predicate'
    else: base=f'reg_{rt}_{idx}'
    if o.kind=='source':
        sw=o.swizzle or 'xyzw'
        if sw!='xyzw': base += '.'+sw
        mod=o.source_modifier or 0
        if mod==1: base='-'+base
        elif mod==2: base=f'({base}-0.5)'
        elif mod==3: base=f'(0.5-{base})'
        elif mod==4: base=f'(({base}*2.0)-1.0)'
        elif mod==5: base=f'(1.0-({base}*2.0))'
        elif mod==6: base=f'(1.0-{base})'
        elif mod==7: base=f'({base}*2.0)'
        elif mod==8: base=f'(-{base}*2.0)'
        elif mod==11: base=f'abs({base})'
        elif mod==12: base=f'-abs({base})'
    return base

def _assign(dst:Operand, expr:str, stage:str='vertex')->str:
    lhs=_glsl_reg(dst,stage)
    if dst.write_mask and dst.write_mask!='xyzw': lhs+='.'+dst.write_mask
    if dst.result_modifier==1: expr=f'clamp({expr},0.0,1.0)'
    return f'{lhs} = {expr};'

def to_glsl(program:ShaderProgram, max_lines:int=10000)->str:
    vs=program.stage=='vertex'
    lines=['#version 310 es','precision highp float;','precision highp int;']
    for i in program.temps: lines.append(f'vec4 r{i}=vec4(0.0);')
    maxc=max(program.constants+[0]); lines.append(f'vec4 c[{max(1,maxc+1)}];')
    for s in program.samplers: lines.append(f'layout(binding={s}) uniform sampler2D tex{s};')
    for x in program.inputs:
        lines.append(f'layout(location={x["register"].split("v")[-1].split(".")[0]}) in vec4 in_{x["register"].split("v")[-1].split(".")[0]};')
    if vs:
        for x in program.outputs: lines.append(f'layout(location={x["index"]}) out vec4 out_{x["index"]};')
    else:
        lines.append('layout(location=0) out vec4 fragColor0;')
    lines.append('void main(){')
    for ins in program.instructions:
        o=ins.operands; n=ins.name
        try:
            if n=='MOV' and len(o)>=2: lines.append('  '+_assign(o[0],_glsl_reg(o[1],program.stage)))
            elif n=='ADD' and len(o)>=3: lines.append('  '+_assign(o[0],f'({_glsl_reg(o[1],program.stage)}+{_glsl_reg(o[2],program.stage)})'))
            elif n=='SUB' and len(o)>=3: lines.append('  '+_assign(o[0],f'({_glsl_reg(o[1],program.stage)}-{_glsl_reg(o[2],program.stage)})'))
            elif n=='MUL' and len(o)>=3: lines.append('  '+_assign(o[0],f'({ _glsl_reg(o[1],program.stage)}*{_glsl_reg(o[2],program.stage)})'))
            elif n=='MAD' and len(o)>=4: lines.append('  '+_assign(o[0],f'(({_glsl_reg(o[1],program.stage)}*{_glsl_reg(o[2],program.stage)})+{_glsl_reg(o[3],program.stage)})'))
            elif n=='DP3' and len(o)>=3: lines.append('  '+_assign(o[0],f'vec4(dot({_glsl_reg(o[1],program.stage)}.xyz,{_glsl_reg(o[2],program.stage)}.xyz))'))
            elif n=='DP4' and len(o)>=3: lines.append('  '+_assign(o[0],f'vec4(dot({_glsl_reg(o[1],program.stage)},{_glsl_reg(o[2],program.stage)}))'))
            elif n=='MIN' and len(o)>=3: lines.append('  '+_assign(o[0],f'min({_glsl_reg(o[1],program.stage)},{_glsl_reg(o[2],program.stage)})'))
            elif n=='MAX' and len(o)>=3: lines.append('  '+_assign(o[0],f'max({_glsl_reg(o[1],program.stage)},{_glsl_reg(o[2],program.stage)})'))
            elif n=='SLT' and len(o)>=3: lines.append('  '+_assign(o[0],f'mix(vec4(0.0),vec4(1.0),lessThan({_glsl_reg(o[1],program.stage)},{_glsl_reg(o[2],program.stage)}))'))
            elif n=='SGE' and len(o)>=3: lines.append('  '+_assign(o[0],f'mix(vec4(0.0),vec4(1.0),greaterThanEqual({_glsl_reg(o[1],program.stage)},{_glsl_reg(o[2],program.stage)}))'))
            elif n=='RCP' and len(o)>=2: lines.append('  '+_assign(o[0],f'(1.0/{_glsl_reg(o[1],program.stage)})'))
            elif n=='RSQ' and len(o)>=2: lines.append('  '+_assign(o[0],f'(1.0/sqrt(abs({_glsl_reg(o[1],program.stage)})))'))
            elif n=='NRM' and len(o)>=2: lines.append('  '+_assign(o[0],f'vec4(normalize({_glsl_reg(o[1],program.stage)}.xyz),0.0)'))
            elif n=='FRC' and len(o)>=2: lines.append('  '+_assign(o[0],f'fract({_glsl_reg(o[1],program.stage)})'))
            elif n=='ABS' and len(o)>=2: lines.append('  '+_assign(o[0],f'abs({_glsl_reg(o[1],program.stage)})'))
            elif n=='POW' and len(o)>=3: lines.append('  '+_assign(o[0],f'pow(abs({_glsl_reg(o[1],program.stage)}),{_glsl_reg(o[2],program.stage)})'))
            elif n=='LRP' and len(o)>=4: lines.append('  '+_assign(o[0],f'mix({_glsl_reg(o[2],program.stage)},{_glsl_reg(o[3],program.stage)},{_glsl_reg(o[1],program.stage)})'))
            elif n=='CMP' and len(o)>=4: lines.append('  '+_assign(o[0],f'mix({_glsl_reg(o[2],program.stage)},{_glsl_reg(o[1],program.stage)},lessThan({_glsl_reg(o[1],program.stage)},vec4(0.0)))'))
            elif n=='TEX' and len(o)>=3: lines.append('  '+_assign(o[0],f'texture({_glsl_reg(o[2],program.stage)}, {_glsl_reg(o[1],program.stage)}.xy)',program.stage))
            elif n=='DSX' and len(o)>=2: lines.append('  '+_assign(o[0],f'dFdx({_glsl_reg(o[1],program.stage)})'))
            elif n=='DSY' and len(o)>=2: lines.append('  '+_assign(o[0],f'dFdy({_glsl_reg(o[1],program.stage)})'))
            elif n in ('IFC','ELSE','ENDIF','LOOP','ENDLOOP','REP','ENDREP'):
                # Control flow requires semantic comparison/type lowering; preserve a visible marker.
                lines.append(f'  /* {n} {len(o)} operands: structured control flow pending */')
            elif n in ('DCL','DEF','DEFI','DEFB'):
                lines.append(f'  /* {n} */')
            else:
                lines.append(f'  /* unsupported {n} opcode={ins.opcode} */')
        except Exception as e:
            lines.append(f'  /* translator error {n}: {e} */')
        if len(lines)>=max_lines: break
    lines.append('}')
    return '\n'.join(lines)+'\n'
