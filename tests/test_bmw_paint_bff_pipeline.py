from bmw_paint_bff_pipeline import _fxo_candidates, _find_basename, _find_exact


class Entry:
    def __init__(self,path):
        self.path=path


def test_bmw_paint_pipeline_exact_and_basename_resolution():
    entries=[Entry('vehicles/BMW_M3_E36/BMW_M3_E36_PAINT.bmt'),Entry('shaders/bodywork.fx')]
    assert len(_find_exact(entries,'vehicles/bmw_m3_e36/bmw_m3_e36_paint.bmt'))==1
    assert len(_find_basename(entries,'bodywork.fx'))==1


def test_bmw_paint_pipeline_fxo_family_is_filtered():
    entries=[Entry('shaders/bodywork_00.fxo'),Entry('shaders/glass_bodywork.fxo'),Entry('shaders/glass.fxo')]
    rows=_fxo_candidates(entries,'bodywork')
    assert [x.path for x in rows]==['shaders/bodywork_00.fxo','shaders/glass_bodywork.fxo']