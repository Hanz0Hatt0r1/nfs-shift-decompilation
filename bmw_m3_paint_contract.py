"""Machine-readable contract for the evidence-backed BMW M3 E36 paint material."""
from __future__ import annotations

from typing import Any, Mapping

FORMAT = "SHIFT.BMWM3PaintMaterialContract/1"

PAINT_CONTRACT = {
    'material_path': 'vehicles/bmw_m3_e36/bmw_m3_e36_paint.bmt',
    'shader': 'bodywork.fx',
    'samplers': [
        {'parameter':'diffuseTexture','fx_sampler':'diffuseMap','register':1,'texture':'COMMON_PAINT.dds','filter':{'min':'Linear','mag':'Linear','mip':'Linear'},'address':{'u':'Wrap','v':'Wrap'},'srgb':True},
        {'parameter':'specularTexture','fx_sampler':'specularMap','register':2,'texture':'COMMON_PAINT_SPECULAR.dds','filter':{'min':'Linear','mag':'Linear','mip':'Linear'},'address':{'u':'Wrap','v':'Wrap'},'srgb':True},
        {'parameter':'scratchControlTexture','fx_sampler':'scratchControlMap','register':4,'texture':'COMMON_BLANK.dds','filter':{'min':'Linear','mag':'Linear','mip':'None'},'address':{'u':'Clamp','v':'Clamp'},'srgb':False},
    ],
    'external_samplers': [
        {'name':'environmentMap','register':3,'sampler_type':'samplerCube','resource':'external-cube','filter':{'min':'Linear','mag':'Linear','mip':'Linear'},'address':{'u':'Clamp','v':'Clamp','w':'Clamp'}},
        {'name':'sShadowMap_f1_0','register':0,'sampler_type':'sampler2D','resource':'external-shadow'},
    ],
    'specializations':['USE_FRESNEL','ALLOW_VINYLS','DIRT_SCRATCH'],
}

def normalize_material_binding(binding: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize current compile_material/MaterialBinding output for this contract."""
    shader_value = binding.get("shader")
    if isinstance(shader_value, Mapping):
        shader_value = shader_value.get("ref") or shader_value.get("path")
    shader_selection = binding.get("shader_selection") or {}
    selected_fxo = shader_selection.get("selected_fxo") or {}
    specializations = (
        binding.get("specializations")
        or binding.get("specialization_flags")
        or binding.get("specialization")
        or selected_fxo.get("specialization_matched")
        or []
    )
    textures = []
    for row in binding.get("textures") or []:
        item = dict(row)
        if item.get("texture") is None and item.get("ref") is not None:
            item["texture"] = item.get("ref")
        if item.get("sampler") is None:
            item["sampler"] = item.get("name")
        textures.append(item)
    return {
        "shader": shader_value,
        "specializations": list(specializations),
        "textures": textures,
        "external_samplers": list(binding.get("external_samplers") or []),
    }


def get_bmw_paint_contract() -> dict[str, Any]:
    return {'format':FORMAT,'status':'documented','contract':PAINT_CONTRACT}

def validate_material_binding(binding: Mapping[str, Any]) -> dict[str, Any]:
    binding = normalize_material_binding(binding)
    reasons=[]; checks=[]
    shader = str(binding.get('shader') or binding.get('shader_path') or '').replace('\\','/').rsplit('/', 1)[-1].lower()
    expected_shader = PAINT_CONTRACT['shader'].lower()
    if shader and shader != expected_shader:
        reasons.append(f'shader:path-mismatch')
    elif not shader:
        reasons.append('shader:path-missing')
    observed_specializations = set(binding.get('specializations') or binding.get('specialization_flags') or [])
    missing_specializations = sorted(set(PAINT_CONTRACT['specializations']) - observed_specializations)
    if missing_specializations:
        reasons.append('specializations:missing:' + ','.join(missing_specializations))
    textures=list(binding.get('textures') or binding.get('bindings') or [])
    for expected in PAINT_CONTRACT['samplers']:
        matches=[row for row in textures if row.get('sampler')==expected['fx_sampler'] or row.get('name')==expected['fx_sampler'] or row.get('material_parameter')==expected['parameter']]

        if len(matches)!=1:
            reasons.append(f"sampler:{expected['fx_sampler']}:expected-one")

            checks.append({'sampler':expected['fx_sampler'],'status':'not-found' if not matches else 'ambiguous'})

            continue
        row=matches[0]; register=row.get('d3d9_sampler_register',row.get('slot'))

        row_check={'sampler':expected['fx_sampler'],'register':register,'expected_register':expected['register'],'texture':row.get('texture'),'expected_texture':expected['texture'],'status':'match'}

        if register!=expected['register']: reasons.append(f"sampler:{expected['fx_sampler']}:register-mismatch"); row_check['status']='mismatch'

        observed_texture=str(row.get('texture') or '').replace('\\','/').rsplit('/',1)[-1].lower()

        if observed_texture and observed_texture!=expected['texture'].lower(): reasons.append(f"sampler:{expected['fx_sampler']}:texture-mismatch"); row_check['status']='mismatch'

        checks.append(row_check)
    external=list(binding.get('external_samplers') or [])
    for expected in PAINT_CONTRACT['external_samplers']:
        matches=[row for row in external if row.get('sampler')==expected['name'] or row.get('name')==expected['name']]

        if len(matches)!=1:

            reasons.append(f"external:{expected['name']}:expected-one")

            continue
        register=matches[0].get('d3d9_sampler_register',matches[0].get('slot'))

        if register!=expected['register']: reasons.append(f"external:{expected['name']}:register-mismatch")

    return {'format':FORMAT,'status':'match' if not reasons else 'mismatch','ready':not reasons,'blocking_reasons':list(dict.fromkeys(reasons)),'checks':checks}