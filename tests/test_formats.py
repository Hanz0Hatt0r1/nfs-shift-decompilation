import sys
import struct
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from resource_formats import parse_bmt_material, parse_reflection_xml, parse_bml, parse_vhf_scene, parse_sgb
from meb_format import read_meb, mesh_summary, write_mgeo
from csm_format import read_csm, csm_summary, write_cmesh
from shift_importer import BFF

ROOT = Path('/mnt/data/dir_bffs')


def test_reflection_scalar_and_vector():
    xml = b'''<?xml version="1.0"?><Reflection>\n<class name="X" base="root"><prop name="A" type="F32"/><prop name="P" type="Vec3"/><prop name="B" type="Bool"/></class>\n<data class="X" id="0x1"><prop name="A" data="1.5"/><prop name="P" data="1;2;3"/><prop name="B" data="true"/></data></Reflection>'''
    r = parse_reflection_xml(xml)
    p = r['objects'][0]['properties']
    assert p['A']['value'] == 1.5
    assert p['P']['value'] == [1.0, 2.0, 3.0]
    assert p['B']['value'] is True


def test_real_bmt_material():
    with BFF(ROOT / 'GUI.bff') as b:
        e = next(e for e in b.entries if e.path.endswith('.bmt'))
        r = parse_bmt_material(b.extract_entry(e))
    m = r['material']
    assert m['name'] == 'HUD_DRIFT_GAUGE'
    assert m['shader'].endswith('hud.fx')
    assert 'GUI/HUD/HUD_DRIFT_GAUGE.dds' in m['textures']
    assert len(m['shaderparams']) >= 2


def test_real_bml_container():
    with BFF(ROOT / 'SCRIPTS.bff') as b:
        e = next(e for e in b.entries if e.path.endswith('.bml'))
        r = parse_bml(b.extract_entry(e))
    assert r['format'] == 'SHIFT.BMLY'
    assert r['version'] == 7
    assert set(r['blocks']) == {'HEAD','ELMT','ATTR','COLL','NUMB','BOOL','STRS'}
    assert r['declared_size'] == r['actual_size']


def test_real_meb_mesh_and_mgeo(tmp_path):
    archive = Path('/mnt/data/Alpental.bff')
    if not archive.exists():
        return
    with BFF(archive) as b:
        e = next(e for e in b.entries if e.path == 'tracks/alpental/grid1_02.meb')
        mesh = read_meb(b.extract_entry(e))
    s = mesh_summary(mesh)
    assert mesh.version == 1
    assert s['vertex_count'] == 4
    assert s['triangle_count'] == 2
    assert '130' in mesh.uv_layers
    assert s['primitives'][0]['material'].lower().endswith('grid2.mtx')
    out = tmp_path / 'grid1_02.mgeo'
    write_mgeo(mesh, out)
    blob = out.read_bytes()
    assert blob[:4] == b'MGEO'
    assert len(blob) > 32


def test_real_csm_collision_mesh(tmp_path):
    archive = Path('/mnt/data/dir_bffs/TRACKS.bff')
    if not archive.exists():
        return
    with BFF(archive) as b:
        e = next(e for e in b.entries if e.path.endswith('.360.csm'))
        mesh = read_csm(b.extract_entry(e))
    s = csm_summary(mesh)
    assert mesh.version == 1
    assert s['vertex_count'] == 363
    assert s['triangle_count'] == 629
    assert s['indices_valid'] is True
    out = tmp_path / 'nord.cmesh'
    write_cmesh(mesh, out)
    assert out.read_bytes()[:4] == b'CMES'


def test_real_meb_skinning_payload():
    archive = Path('/mnt/data/Alpental.bff')
    if not archive.exists():
        return
    with BFF(archive) as b:
        e = next(e for e in b.entries if e.path.endswith('event_flag_vertical_a_org02_loda.meb'))
        mesh = read_meb(b.extract_entry(e))
    assert mesh.vertex_count == 144
    assert len(mesh.bone_weights) == 144
    assert len(mesh.bone_indices) == 144
    assert mesh.skeleton is not None
    assert mesh.skeleton['num_bones'] == 19


def test_vhf_scene_parser():
    data = b"""<?xml version=\"1.0\"?>
<CAR Name=\"TEST\" ExporterVersion=\"Blimey\">
  <NODE type=\"HIERARCHY\" Name=\"Root\" MatrixNumber=\"0\">
    <MATRIX id=\"0\" Offset=\"0 0 0\" Orientation=\"0 0 0 1\"/>
    <NODE type=\"OBJECT\" Name=\"BODY\" MatrixNumber=\"0\">
      <RESOURCE Filename=\"vehicles\\TEST\\BODY.meb\"/>
    </NODE>
  </NODE>
</CAR>
"""
    r = parse_vhf_scene(data)
    assert r["format"] == "SHIFT.VHFScene"
    assert r["stats"]["nodes"] == 2
    assert r["stats"]["resource_refs"] == 1
    assert r["nodes"][0]["children"][0]["resources"][0].endswith("BODY.meb")


def test_sgb_chunk_index():
    def chunk(tag: str, payload: bytes) -> bytes:
        return tag[::-1].encode("ascii") + struct.pack("<I", 8 + len(payload)) + payload
    data = b" \x42\x47\x53" + struct.pack("<III", 0x10, 3, 0)
    data += chunk("NODE", b"abc") + chunk("END ", b"\x00\x00\x00\x00") + b"TAIL"
    r = parse_sgb(data)
    assert r["format"] == "SHIFT.SGB"
    assert [c["tag"] for c in r["chunks"]] == ["NODE", "END "]
    assert r["trailing_bytes"] == 4


def test_fxo_shader_blob_parser():
    from shader_ir import parse_shader_blobs
    from pathlib import Path
    p = Path(__file__).parent / 'fixtures' / 'glass.fxo'
    blobs = parse_shader_blobs(p.read_bytes())
    assert len(blobs) == 4
    assert {b.stage for b in blobs} == {'pixel','vertex'}
    assert all(b.instruction_count > 5 for b in blobs)
    assert all('Microsoft' in ' '.join(b.ctab_strings) for b in blobs)


def test_fx_source_reflection():
    from shader_ir import parse_fx_source
    p = Path(__file__).parent / 'fixtures' / 'basic.fx'
    r = parse_fx_source(p.read_bytes())
    assert 'stddefs.fxh' in r['includes']
    assert len(r['techniques']) >= 2
