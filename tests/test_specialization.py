from specialization import parse_specialisation_params, material_specialisations, feature_signature_score

def test_parse_bodywork_specialisations():
    src='SPECIALISATION_PARAM( useFresnel, "Use Fresnel?", "USE_FRESNEL" )\nSPECIALISATION_PARAM( metallic, "Metallic?", "METALLIC" )'
    r=parse_specialisation_params(src)
    assert [x['flag'] for x in r]==['USE_FRESNEL','METALLIC']

def test_material_feature_inference():
    m={'specializations':['ALLOW_VINYLS'],'shaderparams':[{'name':'fresnelFactor','value':1},{'name':'scratchControlTexture','value':'x'}]}
    assert material_specialisations(m)==['ALLOW_VINYLS','DIRT_SCRATCH','USE_FRESNEL']

def test_feature_signature_score():
    m={'specializations':['USE_FRESNEL','METALLIC','DIRT_SCRATCH']}
    r=feature_signature_score(m,constants=['fresnelFactor','metallicColour','dirtBasis'],samplers=['scratchControlMap'])
    assert r['score']==1.0 and not r['contradicted']