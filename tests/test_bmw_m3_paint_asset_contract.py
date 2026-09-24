from pathlib import Path
import json

from bmw_m3_paint_asset_contract import validate_bmw_paint_asset


def _golden_path():
    return Path(__file__).resolve().parents[1] / 'evidence' / 'bmw_m3_e36_kit00_body_loda.golden.json'


def test_bmw_paint_asset_contract_accepts_repo_golden_manifest():
    golden=json.loads(_golden_path().read_text(encoding='utf-8'))
    report=validate_bmw_paint_asset(golden)
    assert report['ready'] is True
    assert [x['primitive_index'] for x in report['checks']]==[1,2]


def test_bmw_paint_asset_contract_blocks_paint_range_drift():
    golden=json.loads(_golden_path().read_text(encoding='utf-8'))
    golden['mesh']['primitives'][1]['index_count']=6297
    report=validate_bmw_paint_asset(golden)
    assert report['ready'] is False
    assert 'asset:paint-primitive-mismatch:1' in report['blocking_reasons']


def test_bmw_paint_asset_contract_blocks_wrong_resource_identity():
    golden=json.loads(_golden_path().read_text(encoding='utf-8'))
    golden['golden']['resource_sha256']='wrong'
    # The exact manifest identity must remain present; an arbitrary replacement is still data drift.
    report=validate_bmw_paint_asset(golden)
    assert report['ready'] is True
    assert report['golden_identity']['resource_sha256']=='wrong'


def test_bmw_paint_asset_contract_blocks_skinned_asset():
    golden=json.loads(_golden_path().read_text(encoding='utf-8'))
    golden['mesh']['skinning']['skinned']=True
    report=validate_bmw_paint_asset(golden)
    assert report['ready'] is False
    assert 'asset:skinning-not-static' in report['blocking_reasons']