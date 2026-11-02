"""Pixel-grounded repeated input-side symbols can nominate same-color remote objects."""
from collections import defaultdict
from centered_symbol_rows_v1 import tokens
from matrix_intermediate_learner_v3 import gap,inside

def cues(raw,grid):
    if not grid:return []
    groups=defaultdict(list);size=grid['cells'][0][2]
    for t in tokens(raw['frame']):
        y,x,h,w=t['box']
        if not t['hollow'] and h<=size and not inside(y,x,grid['box']) and gap(t['box'],grid['box'])<=12:groups[t['color'],h].append(t)
    out=[]
    for (ink,size),items in groups.items():
        if len(items)<2:continue
        ys=[t['box'][0] for t in items];xs=[t['box'][1] for t in items]
        if max(ys)-min(ys)>16 or max(xs)-min(xs)>16:continue
        out.append(dict(ink=ink,tokens=items,hypothesis='shared_color_reference_may_name_an_interaction_target'))
    return out
