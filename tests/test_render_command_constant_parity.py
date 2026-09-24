from render_command_constant_parity import validate_render_command_constant_parity


def _command(offset=5, count=1):
    return {
        'format':'SHIFT.RenderCommand/1',
        'submeshes':[{'uniforms':{'bindings':[{'name':'Tint','stage':'pixel','register_index':5,'register_count':count,'ctab_type':'float4'}]},
            'constant_payload':{'ready':True,'registers':[{'register_index':5,'values':[1,2,3,4],'byte_offset':80,'byte_size':16}]},
            'constant_commands':[{'name':'Tint','stage':'pixel','register_index':5,'register_count':count,'ctab_type':'float4','byte_offset':offset*16}]}],
    }


def test_constant_parity_accepts_matching_payload_and_command():
    report=validate_render_command_constant_parity(_command(offset=5))
    assert report['ready'] is True
    assert report['checks'][0]['status']=='match'


def test_constant_parity_blocks_wrong_command_offset():
    report=validate_render_command_constant_parity(_command(offset=6))
    assert report['ready'] is False
    assert 'submesh:0:constant:Tint:command-offset' in report['blocking_reasons']


def test_constant_parity_blocks_missing_payload_register():
    command=_command(offset=5)
    command['submeshes'][0]['constant_payload']['registers']=[]
    report=validate_render_command_constant_parity(command)
    assert report['ready'] is False
    assert 'submesh:0:constant:Tint:payload' in report['blocking_reasons']


def test_constant_parity_gate_returns_structured_invalid_format():
    report = validate_render_command_constant_parity({
        "format": "SHIFT.NotRenderCommand/1",
        "submeshes": [],
    })
    assert report["status"] == "invalid"
    assert report["ready"] is False
    assert report["blocking_reasons"] == ["render-command:invalid-format"]


def test_constant_parity_gate_returns_structured_invalid_input_type():
    report = validate_render_command_constant_parity(None)
    assert report["status"] == "invalid"
    assert report["blocking_reasons"] == ["render-command:invalid-input-type"]
