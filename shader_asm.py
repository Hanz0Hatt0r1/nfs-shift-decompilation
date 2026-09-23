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
SEMANTICS={0:'POSITION',1:'BLENDWEIGHT',2:'BLENDINDICES',3:'NORMAL',4:'PSIZE',5:'TEXCOORD',6:'TANGENT',7:'BINORMAL',8:'TESSFACTOR',9:'POSITIONT',10:'COLOR',11:'FOG',12:'DEPTH',13:'SAMPLE'}

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
    predicate:Optional[Operand]=None

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
    const_ints:list[int]=field(default_factory=list)
    const_bools:list[int]=field(default_factory=list)
    sampler_types:dict[int,str]=field(default_factory=dict)


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


def _signed11(v:int)->int:
    return v-0x800 if v&0x400 else v

def _constant_bank(reg_type:int)->tuple[str,int]:
    if reg_type==2: return 'c', 0
    if reg_type==11: return 'c2', 0
    if reg_type==12: return 'c3', 0
    if reg_type==13: return 'c4', 0
    return '', 0

def _physical_constant_index(o:Operand)->int:
    base={2:0,11:2048,12:4096,13:6144}.get(o.reg_type)
    if base is None: return o.index or 0
    idx=_signed11(o.index or 0) if o.relative else (o.index or 0)
    return base+idx

def _decode_params(raw:list[int], opcode:int)->list[Operand]:
    source_only={
        25,26,27,28,29,30,38,39,40,41,42,43,44,45,50,78,80
    }
    dest_first=opcode not in source_only
    operands=[]
    pos=0
    while pos<len(raw):
        token=raw[pos]
        is_dest=dest_first and not operands
        o=decode_dest(token) if is_dest and is_param_token(token) else decode_source(token) if is_param_token(token) else decode_literal(token)
        pos+=1
        if o.relative:
            if pos>=len(raw):
                raise ValueError("relative parameter token missing its address token")
            o.relative_token=raw[pos]
            pos+=1
        operands.append(o)
    return operands

def _sampler_type_from_dcl(tok:int)->str:
    return {
        1:'sampler1D',
        2:'sampler2D',
        3:'samplerCube',
        4:'sampler3D',
    }.get((tok>>27)&0xF, 'sampler2D')

def parse_program(data:bytes, blob_offset:int=0, blob_end:int|None=None, stage:str='unknown', major:int=3, minor:int=0)->ShaderProgram:
    end=len(data) if blob_end is None else blob_end
    pos=blob_offset
    version=struct.unpack_from('<I',data,pos)[0]
    if (version>>16)==0xffff: stage='pixel'
    elif (version>>16)==0xfffe: stage='vertex'
    major=(version>>8)&0xff; minor=version&0xff; pos+=4
    ins=[]; inputs=[]; outputs=[]; samplers=set(); consts=set(); temps=set()
    const_ints=set(); const_bools=set(); sampler_types={}; unsupported=set()
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
        declared_end=pos+(1+ln)*4
        if declared_end>end: break

        if op==31 and len(raw)>=2:
            sem=_literal_for_dcl(raw[0])
            d=decode_dest(raw[1])
            operands=[Operand(token=raw[0],kind='declaration',value=sem,text=f"{sem['usage']}{sem['index']}"),d]
            sem['register']=d.text
            if d.reg_type==10:
                sem['sampler_type']=_sampler_type_from_dcl(raw[0])
                sampler_types[d.index or 0]=sem['sampler_type']
                samplers.add(d.index or 0)
            elif d.reg_type==1:
                inputs.append(sem)
            elif d.reg_type in (4,5,6,8,9):
                outputs.append(sem)
        elif raw and op in (47,48,65):
            # DEFB/DEFI/DEF: everything after the destination is literal payload.
            d=decode_dest(raw[0]) if is_param_token(raw[0]) else decode_literal(raw[0])
            operands=[d]
            for t in raw[1:]:
                operands.append(decode_literal(t))
            if op==48 and d.reg_type==7:
                const_ints.add(d.index or 0)
            elif op==47 and d.reg_type==14:
                const_bools.add(d.index or 0)
            elif op==65 and d.reg_type in (2,11,12,13):
                consts.add(_physical_constant_index(d))
        elif raw:
            operands=_decode_params(raw,op)

        # A predicated instruction carries one extra predicate source token.
        predicate=None
        if pred and operands:
            predicate=operands.pop()

        for x in operands:
            if x.reg_type==10: samplers.add(x.index or 0)
            if x.reg_type in (2,11,12,13): consts.add(_physical_constant_index(x))
            if x.reg_type in (7,): const_ints.add(x.index or 0)
            if x.reg_type in (14,): const_bools.add(x.index or 0)
            if x.reg_type in (0,16): temps.add(x.index or 0)

        name=OPCODES.get(op,f'OP_{op}')
        if name.startswith('OP_'): unsupported.add(op)
        i=Instruction(pos,op,name,tok,ln,(tok>>16)&0xff,pred,operands,predicate)
        ins.append(i)
        pos=declared_end
    return ShaderProgram(
        blob_offset,pos,stage,major,minor,ins,inputs,outputs,sorted(samplers),
        sorted(consts),sorted(temps),sorted(unsupported),
        sorted(const_ints),sorted(const_bools),sampler_types
    )
def _relative_index_expr(o:Operand, stage:str)->str:
    if not o.relative or o.relative_token is None:
        return str(_signed11(o.index or 0))
    rel=decode_source(o.relative_token)
    if rel.reg_type==3:
        rel_expr=f'a{rel.index or 0}'
        rel_sw=rel.swizzle or 'x'
        rel_expr += f'.{rel_sw}'
        rel_expr=f'int({rel_expr})'
    else:
        rel_expr=_glsl_reg(rel,stage)
        rel_expr=f'int({rel_expr})'
    else:
        rel_expr=f'int(round({rel_expr}))'
    off=_signed11(o.index or 0)
    if off==0:
        return f'({rel_expr})'
    sign='+' if off>=0 else '-'
    return f'({rel_expr}{sign}{abs(off)})'

def _glsl_reg(o:Operand, stage:str)->str:
    rt=o.reg_type; idx=o.index or 0
    if rt==0: base=f'r{idx}'
    elif rt==1: base=f'in_{idx}'
    elif rt in (2,11,12,13):
        bank={2:'c',11:'c2',12:'c3',13:'c4'}[rt]
        if o.relative:
            base=f'{bank}[{_relative_index_expr(o,stage)}]'
        else:
            base=f'{bank}[{idx}]'
    elif rt==3:
        base=f'a{idx}' if stage=='vertex' else f'tex{idx}'
    elif rt==4: base=f'vsRastOut{idx}'
    elif rt==5: base=f'vsAttrOut{idx}'
    elif rt==6: base=f'out_{idx}'
    elif rt==8: base=f'fragColor{idx}'
    elif rt==9: base='gl_FragDepth'
    elif rt==10: base=f'tex{idx}'
    elif rt==14: base=f'b[{idx}]'
    elif rt==15: base='ivec4(shift_loop)'
    elif rt==16: base=f'h{idx}'
    elif rt==17: base=f'misc{idx}'
    elif rt==18: base=f'label{idx}'
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
        elif mod==13: base=f'!({base})'
    return base

def _assign(dst:Operand, expr:str, stage:str='vertex', predicate:Operand|None=None)->str:
    lhs=_glsl_reg(dst,stage)
    mask=dst.write_mask or 'xyzw'
    rhs_expr=expr
    if dst.result_modifier==1:
        rhs_expr=f'clamp({rhs_expr},0.0,1.0)'
    if predicate is not None and dst.reg_type not in (19,):
        pred_expr=_glsl_reg(predicate,stage)
        if mask!='xyzw':
            lhs_sw=f'{lhs}.{mask}'
            pred_sw=f'{pred_expr}.{mask}'
            return f'{lhs_sw} = mix({lhs_sw},{rhs_expr}.{mask},{pred_sw});'
        return f'{lhs} = mix({lhs},{rhs_expr},{pred_expr});'
    if mask!='xyzw':
        lhs += '.'+mask
    return f'{lhs} = {rhs_expr};'

def _cmp_expr(a:str,b:str,controls:int)->str:
    cmp_code=controls & 0x7
    aa=f'vec4({a})'
    bb=f'vec4({b})'
    funcs={
        1:'greaterThan',
        2:'equal',
        3:'greaterThanEqual',
        4:'lessThan',
        5:'notEqual',
        6:'lessThanEqual',
    }
    fn=funcs.get(cmp_code)
    if fn is None:
        return 'bvec4(false)'
    return f'{fn}({aa},{bb})'

def _bool_condition(o:Operand,stage:str)->str:
    x=_glsl_reg(o,stage)
    if o.reg_type in (14,19) and (o.swizzle or 'x') in ('x','r'):
        return f'({x})'
    return f'all({x})'

def _tex_coord(coord:Operand, sampler:Operand, program:ShaderProgram)->str:
    c=_glsl_reg(coord,program.stage)
    st=program.sampler_types.get(sampler.index or 0,'sampler2D')
    if st=='sampler1D':
        return f'{c}.x'
    if st in ('samplerCube','sampler3D'):
        return f'{c}.xyz'
    return f'{c}.xy'

def _bank_size(program:ShaderProgram, reg_type:int)->int:
    m=0
    for ins in program.instructions:
        for o in ins.operands:
            if o.reg_type==reg_type:
                m=max(m,(o.index or 0)+1)
        pred=getattr(ins,'predicate',None)
        if pred is not None and pred.reg_type==reg_type:
            m=max(m,(pred.index or 0)+1)
    return max(1,m)

def _emit_matrix(dst:Operand, src:Operand, mat:Operand, rows:int, cols:int, stage:str)->str:
    v=_glsl_reg(src,stage)
    bank={2:'c',11:'c2',12:'c3',13:'c4'}.get(mat.reg_type or 2,'c')
    base=_signed11(mat.index or 0) if mat.relative else (mat.index or 0)
    rel=f'[{_relative_index_expr(mat,stage)}]' if mat.relative else '[0]'
    comps=[]
    for row in range(rows):
        mref=f'{bank}[{base+row}]' if not mat.relative else f'{bank}[{_relative_index_expr(mat,stage)}+{row}]'
        comps.append(f'dot({v}.{"xyz" if cols==3 else "xyzw"},{mref}.{"xyz" if cols==3 else "xyzw"})')
    expr='vec4('+','.join(comps)+')'
    return _assign(dst,expr,stage,getattr(dst,'predicate',None))

def to_glsl(program:ShaderProgram, max_lines:int=10000)->str:
    lines=['#version 310 es','precision highp float;','precision highp int;']
    for i in program.temps: lines.append(f'vec4 r{i}=vec4(0.0);')
    for bank,rt in (('c',2),('c2',11),('c3',12),('c4',13)):
        lines.append(f'vec4 {bank}[{_bank_size(program,rt)}];')
    lines.append(f'ivec4 i[{max(1,max(program.const_ints+[0])+1)}];')
    lines.append(f'bvec4 b[{max(1,max(program.const_bools+[0])+1)}];')
    lines.append('ivec4 a0=ivec4(0);')
    lines.append('bvec4 predicate=bvec4(false);')
    for s in program.samplers:
        sampler_type=program.sampler_types.get(s,'sampler2D')
        lines.append(f'layout(binding={s}) uniform {sampler_type} tex{s};')
    for x in program.inputs:
        reg=str(x.get('register','v0'))
        try: loc=int(reg.split('v',1)[1].split('.',1)[0])
        except Exception: loc=0
        lines.append(f'layout(location={loc}) in vec4 in_{loc};')
    if program.stage=='vertex':
        for x in program.outputs:
            lines.append(f'layout(location={x.get("index",0)}) out vec4 out_{x.get("index",0)};')
    else:
        lines.append('layout(location=0) out vec4 fragColor0;')
    lines.append('void main(){')

    rep_depth=0
    loop_depth=0
    for ins in program.instructions:
        o=ins.operands; n=ins.name
        pred=getattr(ins,'predicate',None)
        try:
            if n in ('NOP','DCL','DEF','DEFI','DEFB','LABEL','COMMENT','PHASE'):
                continue
            if n=='MOV' and len(o)>=2:
                lines.append('  '+_assign(o[0],_glsl_reg(o[1],program.stage),program.stage,pred))
            elif n=='ADD' and len(o)>=3: lines.append('  '+_assign(o[0],f'({_glsl_reg(o[1],program.stage)}+{_glsl_reg(o[2],program.stage)})',program.stage,pred))
            elif n=='SUB' and len(o)>=3: lines.append('  '+_assign(o[0],f'({_glsl_reg(o[1],program.stage)}-{_glsl_reg(o[2],program.stage)})',program.stage,pred))
            elif n=='MUL' and len(o)>=3: lines.append('  '+_assign(o[0],f'({_glsl_reg(o[1],program.stage)}*{_glsl_reg(o[2],program.stage)})',program.stage,pred))
            elif n=='MAD' and len(o)>=4: lines.append('  '+_assign(o[0],f'(({_glsl_reg(o[1],program.stage)}*{_glsl_reg(o[2],program.stage)})+{_glsl_reg(o[3],program.stage)})',program.stage,pred))
            elif n=='DP3' and len(o)>=3: lines.append('  '+_assign(o[0],f'vec4(dot({_glsl_reg(o[1],program.stage)}.xyz,{_glsl_reg(o[2],program.stage)}.xyz))',program.stage,pred))
            elif n=='DP4' and len(o)>=3: lines.append('  '+_assign(o[0],f'vec4(dot({_glsl_reg(o[1],program.stage)},{_glsl_reg(o[2],program.stage)}))',program.stage,pred))
            elif n=='MIN' and len(o)>=3: lines.append('  '+_assign(o[0],f'min({_glsl_reg(o[1],program.stage)},{_glsl_reg(o[2],program.stage)})',program.stage,pred))
            elif n=='MAX' and len(o)>=3: lines.append('  '+_assign(o[0],f'max({_glsl_reg(o[1],program.stage)},{_glsl_reg(o[2],program.stage)})',program.stage,pred))
            elif n=='SLT' and len(o)>=3: lines.append('  '+_assign(o[0],f'mix(vec4(0.0),vec4(1.0),lessThan({_glsl_reg(o[1],program.stage)},{_glsl_reg(o[2],program.stage)}))',program.stage,pred))
            elif n=='SGE' and len(o)>=3: lines.append('  '+_assign(o[0],f'mix(vec4(0.0),vec4(1.0),greaterThanEqual({_glsl_reg(o[1],program.stage)},{_glsl_reg(o[2],program.stage)}))',program.stage,pred))
            elif n=='EXP' and len(o)>=2: lines.append('  '+_assign(o[0],f'vec4(exp2({_glsl_reg(o[1],program.stage)}))',program.stage,pred))
            elif n=='EXPP' and len(o)>=2: lines.append('  '+_assign(o[0],f'vec4(exp2({_glsl_reg(o[1],program.stage)}))',program.stage,pred))
            elif n=='LOG' and len(o)>=2: lines.append('  '+_assign(o[0],f'vec4(log2({_glsl_reg(o[1],program.stage)}))',program.stage,pred))
            elif n=='LOGP' and len(o)>=2: lines.append('  '+_assign(o[0],f'vec4(log2({_glsl_reg(o[1],program.stage)}))',program.stage,pred))
            elif n=='LIT' and len(o)>=2:
                x=_glsl_reg(o[1],program.stage)
                expr=f'vec4(1.0,max({x}.x,0.0),(({x}.y>0.0)?pow(max({x}.y,0.0),clamp({x}.w,-128.0,128.0)):0.0),1.0)'
                lines.append('  '+_assign(o[0],expr,program.stage,pred))
            elif n=='DST' and len(o)>=3:
                a=_glsl_reg(o[1],program.stage); b_= _glsl_reg(o[2],program.stage)
                lines.append('  '+_assign(o[0],f'vec4(1.0,{a}.y*{b_}.y,{a}.z,{b_}.w)',program.stage,pred))
            elif n=='LRP' and len(o)>=4:
                lines.append('  '+_assign(o[0],f'mix({_glsl_reg(o[3],program.stage)},{_glsl_reg(o[2],program.stage)},{_glsl_reg(o[1],program.stage)})',program.stage,pred))
            elif n=='FRC' and len(o)>=2: lines.append('  '+_assign(o[0],f'fract({_glsl_reg(o[1],program.stage)})',program.stage,pred))
            elif n in ('RCP',) and len(o)>=2: lines.append('  '+_assign(o[0],f'(1.0/{_glsl_reg(o[1],program.stage)})',program.stage,pred))
            elif n=='RSQ' and len(o)>=2: lines.append('  '+_assign(o[0],f'(1.0/sqrt(abs({_glsl_reg(o[1],program.stage)})))',program.stage,pred))
            elif n=='NRM' and len(o)>=2: lines.append('  '+_assign(o[0],f'normalize({_glsl_reg(o[1],program.stage)})',program.stage,pred))
            elif n=='POW' and len(o)>=3: lines.append('  '+_assign(o[0],f'pow({_glsl_reg(o[1],program.stage)},{_glsl_reg(o[2],program.stage)})',program.stage,pred))
            elif n=='CRS' and len(o)>=3: lines.append('  '+_assign(o[0],f'vec4(cross({_glsl_reg(o[1],program.stage)}.xyz,{_glsl_reg(o[2],program.stage)}.xyz),0.0)',program.stage,pred))
            elif n=='SGN' and len(o)>=2: lines.append('  '+_assign(o[0],f'sign({_glsl_reg(o[1],program.stage)})',program.stage,pred))
            elif n=='SINCOS' and len(o)>=2:
                x=_glsl_reg(o[1],program.stage)
                lines.append('  '+_assign(o[0],f'vec4(sin({x}),cos({x}),0.0,0.0)',program.stage,pred))
            elif n in ('M4x4','M4x3','M3x4','M3x3','M3x2') and len(o)>=3:
                dims={'M4x4':(4,4),'M4x3':(4,3),'M3x4':(3,4),'M3x3':(3,3),'M3x2':(3,2)}[n]
                dst=o[0]; src=o[1]; mat=o[2]
                rows,cols=dims
                v=_glsl_reg(src,program.stage)
                bank={2:'c',11:'c2',12:'c3',13:'c4'}.get(mat.reg_type or 2,'c')
                if mat.relative:
                    refs=[f'{bank}[{_relative_index_expr(mat,program.stage)}+{r}]' for r in range(rows)]
                else:
                    base=mat.index or 0
                    refs=[f'{bank}[{base+r}]' for r in range(rows)]
                vv=f'{v}.xyz' if cols==3 else f'{v}.xyzw'
                parts=[f'dot({vv},{m}.{"xyz" if cols==3 else "xyzw"})' for m in refs]
                expr=('vec4('+','.join(parts)+')') if len(parts)==4 else ('vec3('+','.join(parts)+')' if len(parts)==3 else 'vec2('+','.join(parts)+')')
                lines.append('  '+_assign(dst,expr,program.stage,pred))
            elif n=='CMP' and len(o)>=4:
                lines.append('  '+_assign(o[0],f'mix({_glsl_reg(o[3],program.stage)},{_glsl_reg(o[2],program.stage)},greaterThanEqual({_glsl_reg(o[1],program.stage)},vec4(0.0)))',program.stage,pred))
            elif n=='DP2ADD' and len(o)>=4:
                a=_glsl_reg(o[1],program.stage); b_= _glsl_reg(o[2],program.stage); c_= _glsl_reg(o[3],program.stage)
                lines.append('  '+_assign(o[0],f'vec4(dot({a}.xy,{b_}.xy)+{c_}.x)',program.stage,pred))
            elif n=='TEX' and len(o)>=3:
                coord=_tex_coord(o[1],o[2],program)
                lines.append('  '+_assign(o[0],f'texture({_glsl_reg(o[2],program.stage)},{coord})',program.stage,pred))
            elif n=='TEXLDD' and len(o)>=5:
                coord=_tex_coord(o[1],o[2],program)
                lines.append('  '+_assign(o[0],f'textureGrad({_glsl_reg(o[2],program.stage)},{coord},{_glsl_reg(o[3],program.stage)}.xy,{_glsl_reg(o[4],program.stage)}.xy)',program.stage,pred))
            elif n=='TEXLDL' and len(o)>=3:
                coord=_tex_coord(o[1],o[2],program)
                fullcoord=_glsl_reg(o[1],program.stage)
                lines.append('  '+_assign(o[0],f'textureLod({_glsl_reg(o[2],program.stage)},{coord},{fullcoord}.w)',program.stage,pred))
            elif n=='TEXKILL' and len(o)>=1:
                x=_glsl_reg(o[0],program.stage)
                lines.append(f'  if(any(lessThan({x}.xyz,vec3(0.0))) ) discard;')
            elif n=='DSX' and len(o)>=2: lines.append('  '+_assign(o[0],f'dFdx({_glsl_reg(o[1],program.stage)})',program.stage,pred))
            elif n=='DSY' and len(o)>=2: lines.append('  '+_assign(o[0],f'dFdy({_glsl_reg(o[1],program.stage)})',program.stage,pred))
            elif n=='SETP' and len(o)>=3:
                cmp=_cmp_expr(_glsl_reg(o[1],program.stage),_glsl_reg(o[2],program.stage),ins.controls)
                lines.append('  '+_assign(o[0],cmp,program.stage))
            elif n=='IF' and len(o)>=1:
                lines.append(f'  if {_bool_condition(o[0],program.stage)} {{')
            elif n=='IFC' and len(o)>=2:
                cmp=_cmp_expr(_glsl_reg(o[0],program.stage),_glsl_reg(o[1],program.stage),ins.controls)
                lines.append(f'  if(all({cmp})) {{')
            elif n=='ELSE': lines.append('  } else {')
            elif n=='ENDIF': lines.append('  }')
            elif n=='BREAK': lines.append('  break;')
            elif n=='BREAKC' and len(o)>=2:
                cmp=_cmp_expr(_glsl_reg(o[0],program.stage),_glsl_reg(o[1],program.stage),ins.controls)
                lines.append(f'  if(all({cmp})) break;')
            elif n=='BREAKP' and len(o)>=1:
                lines.append(f'  if({_bool_condition(o[0],program.stage)}) break;')
            elif n=='LOOP' and len(o)>=1:
                src=_glsl_reg(o[0],program.stage)
                loop_depth+=1
                lines.append(f'  for(int shift_loop=int(round({src}.y)), shift_iter=0; shift_iter<int(round({src}.x)); ++shift_iter, shift_loop+=int(round({src}.z))) {{')
            elif n=='ENDLOOP':
                loop_depth=max(0,loop_depth-1)
                lines.append('  }')
            elif n=='REP' and len(o)>=1:
                src=_glsl_reg(o[0],program.stage)
                rep_depth+=1
                lines.append(f'  for(int shift_rep{rep_depth}=0; shift_rep{rep_depth}<int({src}.x); ++shift_rep{rep_depth}) {{')
            elif n=='ENDREP':
                lines.append('  }')
                rep_depth=max(0,rep_depth-1)
            elif n=='MOVA' and len(o)>=2:
                lhs=_glsl_reg(o[0],program.stage)
                mask=o[0].write_mask or 'xyzw'
                rhs=f'ivec4(round({_glsl_reg(o[1],program.stage)}))'
                if mask!='xyzw':
                    lhs += '.'+mask
                    rhs += '.'+mask
                lines.append(f'  {lhs} = {rhs};')
            elif n=='RET':
                lines.append('  return;')
            else:
                lines.append(f'  /* unsupported {n} opcode={ins.opcode} */')
        except Exception as e:
            lines.append(f'  /* translator error {n}: {e} */')
        if len(lines)>=max_lines: break
    lines.append('}')
    return '\n'.join(lines)+'\n'