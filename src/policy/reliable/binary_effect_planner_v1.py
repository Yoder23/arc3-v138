"""Solve observed binary action effects without Cartesian state enumeration."""
def plan(current,allowed,models,palette):
    if len(palette)!=2 or any(v not in palette for v in current.values()):return None
    a,b=palette
    usable={p:m for p,m in sorted(models.items()) if m['ready'] and m['transitions']
        and all(q in current and d=={a:b,b:a} for q,d in m['transitions'].items())}
    points=list(usable);equations=[]
    for q,values in sorted(allowed.items()):
        if not values:return None
        if len(values)==2:continue
        if q not in current or len(values)!=1 or values[0] not in palette:return None
        mask=sum(1<<i for i,p in enumerate(points) if q in usable[p]['transitions'])
        equations.append([mask,int(current[q]!=values[0])])
    # Row echelon over GF(2), with free action parities fixed at zero.
    pivots={}
    for mask,rhs in equations:
        while mask:
            bit=(mask&-mask).bit_length()-1
            if bit not in pivots:pivots[bit]=(mask,rhs);break
            other,value=pivots[bit];mask^=other;rhs^=value
        else:
            if rhs:return None
    result=0
    for bit,(mask,rhs) in sorted(pivots.items(),reverse=True):
        if ((mask&result).bit_count()&1)!=rhs:result|=1<<bit
    selected=[p for i,p in enumerate(points) if result>>i&1]
    state=dict(current)
    for p in selected:
        for q,d in usable[p]['transitions'].items():state[q]=d[state[q]]
    if not all(state[p] in values for p,values in allowed.items()):return None
    return selected
