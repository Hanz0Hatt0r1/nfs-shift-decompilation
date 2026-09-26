import sys

sys.path.insert(0, '/mnt/data')

import bmw_m3_runtime_material_witness as witness


def _draw_block(
    call,
    prim,
    ib,
    *,
    vs='0x111',
    ps='0x222',
    vertex_values=(),
    pixel_values=(),
    textures=((1, '0xaaa'),),
):
    vertex_values = list(vertex_values)
    pixel_values = list(pixel_values)
    lines = [
        f'{call-8} IDirect3DDevice9::SetStreamSource(this = 0x1, StreamNumber = 0, pStreamData = 0x27b39460, OffsetInBytes = 0, Stride = 76) = D3D_OK',
        f'{call-7} IDirect3DDevice9::SetIndices(this = 0x1, pIndexData = {ib}) = D3D_OK',
        f'{call-6} IDirect3DDevice9::SetVertexShader(this = 0x1, pShader = {vs}) = D3D_OK',
    ]
    if vertex_values:
        lines.append(
            f'{call-5} IDirect3DDevice9::SetVertexShaderConstantF(this = 0x1, StartRegister = 0, '
            f'pConstantData = {{{", ".join(str(x) for x in vertex_values)}}}, Vector4fCount = {len(vertex_values)//4}) = D3D_OK'
        )
    lines.append(f'{call-4} IDirect3DDevice9::SetPixelShader(this = 0x1, pShader = {ps}) = D3D_OK')
    if pixel_values:
        lines.append(
            f'{call-3} IDirect3DDevice9::SetPixelShaderConstantF(this = 0x1, StartRegister = 0, '
            f'pConstantData = {{{", ".join(str(x) for x in pixel_values)}}}, Vector4fCount = {len(pixel_values)//4}) = D3D_OK'
        )
    for offset, (stage, ptr) in enumerate(textures, start=-2):
        lines.append(f'{call+offset} IDirect3DDevice9::SetTexture(this = 0x1, Stage = {stage}, pTexture = {ptr}) = D3D_OK')
    lines.append(
        f'{call} IDirect3DDevice9::DrawIndexedPrimitive(this = 0x1, PrimitiveType = D3DPT_TRIANGLELIST, '
        f'BaseVertexIndex = 0, MinVertexIndex = 0, NumVertices = 3550, startIndex = 0, primCount = {prim}) = D3D_OK'
    )
    return '\n'.join(lines) + '\n'


def _bank_with_vectors(vectors):
    data = [0.0] * (max((register for register, _ in vectors), default=-1) + 1) * 4
    for register, value in vectors:
        data[register * 4:register * 4 + 4] = value
    return data


def test_parse_frame_draws_captures_draw_local_state():
    text = _draw_block(
        100,
        192,
        '0x27b396e0',
        vertex_values=_bank_with_vectors([(8, [0.42, 0.0, 0.0, 0.0])]),
        pixel_values=_bank_with_vectors([(26, [8192.0, 0.0, 0.0, 0.0])]),
    )
    rows = witness.parse_frame_dump(text)
    assert len(rows) == 1
    row = rows[0]
    assert row['call'] == 100
    assert row['primitive_count'] == 192
    assert row['base_vertex_index'] == 0
    assert row['min_vertex_index'] == 0
    assert row['index_buffer'] == '0x27b396e0'
    assert row['vertex_shader'] == '0x111'
    assert row['pixel_shader'] == '0x222'
    assert row['constant_banks']['pixel']['26'] == [8192.0, 0.0, 0.0, 0.0]
    assert row['texture_bindings']['1'] == '0xaaa'


def test_each_material_profile_has_distinct_draw_local_witnesses():
    for profile in witness.MATERIAL_WITNESS_PROFILE:
        stages = {'vertex': [], 'pixel': []}
        for item in profile['witnesses']:
            register = 0
            for other in profile['witnesses']:
                if other is item:
                    break
                if other['stage'] == item['stage']:
                    register += 1
            stages[item['stage']].append((register, item['value']))
        rows = witness.parse_frame_dump(
            _draw_block(
                100,
                profile['primitive_counts'][0],
                '0x27b394e0',
                vertex_values=_bank_with_vectors(stages['vertex']),
                pixel_values=_bank_with_vectors(stages['pixel']),
            )
        )
        assert witness.match_draw(rows[0], profile)['ready'] is True


def test_material_matching_is_draw_local_and_does_not_cross_correlate():
    gloss = witness.MATERIAL_WITNESS_PROFILE[3]
    good = _draw_block(
        100,
        192,
        '0x27b396e0',
        vertex_values=_bank_with_vectors([(8, [0.42, 0.0, 0.0, 0.0])]),
        pixel_values=_bank_with_vectors([(26, [8192.0, 0.0, 0.0, 0.0])]),
    )
    bad = _draw_block(
        200,
        50,
        '0x27b394e0',
        vertex_values=_bank_with_vectors([(8, [0.42, 0.0, 0.0, 0.0])]),
        pixel_values=_bank_with_vectors([(26, [0.0, 0.0, 0.0, 0.0])]),
    )
    draws = witness.parse_frame_dump(good + bad)
    assert witness.match_draw(draws[0], gloss)['ready'] is True
    assert witness.match_draw(draws[1], gloss)['ready'] is False


def test_validation_rejects_unexpected_target_draw_count():
    report = witness.build_report(_draw_block(
        100,
        192,
        '0x27b396e0',
        vertex_values=_bank_with_vectors([(8, [0.42, 0.0, 0.0, 0.0])]),
        pixel_values=_bank_with_vectors([(26, [8192.0, 0.0, 0.0, 0.0])]),
    ))
    reasons = witness.validate_report(report)
    assert any(reason.startswith('draw-count:expected-28') for reason in reasons)
