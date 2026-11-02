from compartment_prerequisites_v1b import proposals as fill_proposals
import math
def proposals(s,g,models,trials):
    out=[];axis=g['axis'];orth=1-axis
    for b in s['buttons']:
        box=b['box']
        if box[axis+2]<=box[orth+2]:continue
        left=[i for i,z in enumerate(g['segments'])if 0<=box[orth]-z['span'][1]<=box[orth+2]]
        right=[i for i,z in enumerate(g['segments'])if 0<=z['span'][0]-box[orth]-box[orth+2]<=box[orth+2]]
        if len(left)!=1 or len(right)!=1:continue
        a,c=left[0],right[0]
        steps=[abs(v)for d in models.values()for v in d if v];step=math.gcd(*steps)if steps else 1
        values=sorted(range(box[axis],box[axis]+box[axis+2]+1),key=lambda v:(abs(v-s['positions'][a])+abs(v-s['positions'][c]),v))
        for value in values:
            if (value-s['positions'][a])%step or(value-s['positions'][c])%step:continue
            key=(a,c,value)
            if key in trials:continue
            target=[None]*len(s['positions']);target[a]=target[c]=value
            out.append(dict(index=a,target=value,targets=target,key=key,aperture=b,conditional_click=True,reason='Test reachable matched neighboring boundaries inside a visible aperture, then retry its interaction.'))
    for p in fill_proposals(s,g,models,trials):p['key']=(p['index'],p['target']);out.append(p)
    return out
