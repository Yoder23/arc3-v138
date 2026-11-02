"""Recognize bounded two-stage editable dictionaries through a shared alphabet."""
from editable_word_programs import layouts as direct,signature as direct_signature
from panel_hypotheses_v2 import rectangles,digest
from panel_sequence_hypotheses import glyphs
from panel_control_learner import identity

def layouts(obs):
    base=direct(obs);out=list(base)
    rects=[dict(r,symbols=glyphs(r)) for r in rectangles(obs['frame']) if glyphs(r)]
    for first in base:
        for second in base:
            if first['target_background']!=second['source_background'] or first['axis']!=second['axis']:continue
            if first['source_background']==second['target_background']:continue
            pairs=first['pairs']+second['pairs']
            used={tuple(p['box']) for pair in pairs for p in pair}
            if len(used)!=2*len(pairs):continue
            panels=sorted([p for pair in pairs for p in pair],key=lambda p:p['box'])
            queries=[]
            for a in rects:
                if tuple(a['box']) in used or a['background']!=first['source_background'] or len(a['symbols'])<2:continue
                for b in rects:
                    if tuple(b['box']) in used or b['background']!=second['target_background'] or len(b['symbols'])<2:continue
                    y,x,Y,X=a['box'];r,c,R,C=b['box'];h=Y-y+1;w=X-x+1;H=R-r+1;W=C-c+1
                    aligned=(first['axis']=='horizontal' and w>h and W>H and h==H and abs(x+X-c-C)<=1) or (
                        first['axis']=='vertical' and h>w and H>W and w==W and abs(y+Y-r-R)<=1)
                    if aligned:queries.append(dict(source_box=a['box'],target_box=b['box'],
                        source=tuple(identity(g['mask']) for g in a['symbols']),
                        target=tuple(identity(g['mask']) for g in b['symbols']),observation=digest(obs)))
            out.append(dict(kind='composed_editable_word_layout',source_background=first['source_background'],
                target_background=second['target_background'],intermediate_background=first['target_background'],
                axis=first['axis'],pairs=pairs,panels=panels,queries=queries,
                schema=(first['schema'],second['schema']),stages=(first,second)))
    return out

def signature(layout):
    if layout.get('kind')!='composed_editable_word_layout':return direct_signature(layout)
    return ('composed',layout['source_background'],layout['intermediate_background'],
            layout['target_background'],layout['axis'],layout['schema'])
