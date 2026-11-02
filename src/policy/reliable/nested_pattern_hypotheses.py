"""Infer a miniature-pattern-to-neighborhood correspondence from visible examples."""
from collections import defaultdict
import numpy as np
from nested_pattern_perception import representations

def expected(marker,rule,palette):
    center=marker['pattern'][1][1];other=set(palette)-{center}
    if len(other)!=1:return None
    other=next(iter(other));ink,flip,turn=rule
    pattern=np.asarray(marker['pattern']);pattern=np.rot90(np.fliplr(pattern) if flip else pattern,turn)
    if ink not in {int(pattern[y,x]) for y in range(3) for x in range(3) if (y,x)!=(1,1)}:return None
    return tuple(center if pattern[y,x]==ink else other for y in range(3) for x in range(3) if (y,x)!=(1,1))

def candidates(frame,remembered=()):
    outputs=[]
    for scene in representations(frame):
        palette={c for y,x,c in scene['cells']}|{m['pattern'][1][1] for m in scene['markers']}
        if len(palette)!=2:continue
        inks=sorted({v for m in scene['markers'] for row in m['pattern'] for v in row}-palette)
        live=[]
        for ink in inks:
            for flip in (False,True):
                for turn in range(4):
                    rule=(ink,flip,turn)
                    matched=[m for m in scene['markers'] if expected(m,rule,palette)==m['colors']]
                    if len(matched)>=3:live.append(dict(rule=rule,examples=matched))
        choices=live or list(remembered)
        for choice in choices:
            desired=defaultdict(set);supported=True
            for m in scene['markers']:
                values=expected(m,choice['rule'],palette)
                if values is None:supported=False;break
                for p,value in zip(m['neighbors'],values):desired[p].add(value)
            if not supported or any(len(v)!=1 for v in desired.values()):continue
            outputs.append(dict(scene=scene,rule=choice['rule'],examples=choice['examples'],live=bool(live),
                desired={p:next(iter(v)) for p,v in desired.items()},
                scope='Tentative mini-pattern correspondence supported by completed visible neighborhoods; observed progress is required to establish task sufficiency.'))
    return outputs
