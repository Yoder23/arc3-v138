"""Reference cues may be remote framed masks; preserve the older local-token fallback."""
from matrix_reference_cues_v1 import cues as local_cues
from matrix_reference_programs_v1 import programs

def cues(raw,grid):
    found=programs(raw['frame'],grid)
    if not found:return local_cues(raw,grid)
    return [dict(ink=p['ink'],tokens=[dict(box=p['cells'][i]['box'],core=p['cells'][i]['box'],color=p['ink'],value=p['ink'],hollow=False) for i in p['indices']],program=p,hypothesis='shared_color_reference_may_name_an_interaction_target') for p in found]
