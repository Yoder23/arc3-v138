"""Tentative body continuity across small enclosed pixel substitutions."""
import numpy as np
from scipy.ndimage import binary_fill_holes,label
from visual_transform_learner import parts,canonical,digest

def complete(shape):
    height=max(y for y,x in shape)+1;width=max(x for y,x in shape)+1
    mask=np.zeros((height,width),bool)
    for y,x in shape:mask[y,x]=True
    filled=binary_fill_holes(mask);holes=filled&~mask
    missing=int(holes.sum());area=int(filled.sum())
    if not 0<missing<=max(1,area//8):return None
    labels,n=label(holes)
    if any(int((labels==i).sum())>1 for i in range(1,n+1)):return None
    return tuple(map(tuple,np.argwhere(filled).tolist())),tuple(map(tuple,np.argwhere(holes).tolist()))

def candidates(observation,source,template):
    assert template in parts(source['frame'])
    result=[]
    for raw in parts(observation['frame']):
        if raw[0]!=template[0]:continue
        change=complete(raw[1])
        if change is None:continue
        shape,holes=change
        if canonical(shape)!=canonical(template[1]):continue
        result.append(dict(kind='observed_body_completion',raw_pose=raw,
            completed_pose=(raw[0],shape,raw[2]),missing_interior_pixels=holes,
            source_pose=template,source_context=digest(source),context=digest(observation),
            scope='Small enclosed substitutions match an earlier actually observed body. This is a continuity hypothesis; no hidden body or goal semantics asserted.'))
    return result
