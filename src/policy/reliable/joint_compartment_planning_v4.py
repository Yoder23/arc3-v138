"""Compose observed boundary motion with a tested conditional marker transfer."""
import heapq
from fractions import Fraction

def layout(s,g):
    axis=g['axis'];orth=1-axis;segments=g['segments'];markers=[];goals=[];gates=[]
    for p in s['pairs']:
        at=p['actor']['box'][orth]+p['actor']['box'][orth+2]/2
        hits=[i for i,z in enumerate(segments)if z['span'][0]<=at<z['span'][1] and z['bounds'][0]<=p['current']<=z['bounds'][1]]
        if len(hits)!=1:return None
        markers.append(hits[0]);box=p['reference']['box']
        adjacent=[i for i,z in enumerate(segments)if (0<=box[orth]-z['span'][1]<=box[orth+2]or 0<=z['span'][0]-box[orth]-box[orth+2]<=box[orth+2]) and z['bounds'][0]<=p['target']<=z['bounds'][1]]
        binding=next(b for b in g['bindings']if b['ink']==p['ink'])
        if not adjacent:return None
        goals.append((tuple(adjacent),p['target']-binding['offset']))
    for i,b in enumerate(s['buttons']):
        box=b['box']
        if box[axis+2]<=box[orth+2]:continue
        left=[j for j,z in enumerate(segments)if 0<=box[orth]-z['span'][1]<=box[orth+2] and max(z['bounds'][0],box[axis])<min(z['bounds'][1],box[axis]+box[axis+2])]
        right=[j for j,z in enumerate(segments)if 0<=z['span'][0]-box[orth]-box[orth+2]<=box[orth+2] and max(z['bounds'][0],box[axis])<min(z['bounds'][1],box[axis]+box[axis+2])]
        if len(left)==len(right)==1:gates.append((i,left[0],right[0],box[axis],box[axis]+box[axis+2]))
    return dict(markers=tuple(markers),goals=goals,gates=gates)

def advance(state,index,models,gates,bounds):
    water,markers=state
    if index in models:
        q=tuple(v+d for v,d in zip(water,models[index]))
        if all(lo<=v<=hi for v,(lo,hi)in zip(q,bounds)):return(q,markers)
    for i,a,b,lo,hi in gates:
        if i==index and water[a]==water[b]and lo<=water[a]<=hi:
            m=tuple(b if v==a else a if v==b else v for v in markers)
            if m!=markers:return(water,m)
    return None

def search(water,L,models,bounds,blocked,limit=80000):
    start=(tuple(water),L['markers']);goals=L['goals'];gates=L['gates']
    actions=sorted(set(models)|{g[0]for g in gates});step=max([abs(v)for d in models.values()for v in d]+[1])
    def success(state):
        q,m=state;return all(at in allowed and q[at]==value for at,(allowed,value)in zip(m,goals))
    def h(state):
        q,m=state
        return sum(min(abs(at-b)for b in allowed)*3+abs(q[at]-value)/(step*2)for at,(allowed,value)in zip(m,goals))
    if success(start):return []
    queue=[(h(start),0,start,[])];best={start:0};n=0
    while queue and n<limit:
        _,cost,state,path=heapq.heappop(queue);n+=1
        if cost!=best[state]or cost>=100:continue
        if success(state):return path
        for index in actions:
            if signature(state,index,models,gates)in blocked:continue
            after=advance(state,index,models,gates,bounds)
            if after is None or cost+1>=best.get(after,10**9):continue
            best[after]=cost+1;heapq.heappush(queue,(cost+1+1.5*h(after),cost+1,after,path+[(index,after)]))
    return None


def signature(state,index,models,gates):
    water,markers=state
    selected=set()
    for i,a,b,lo,hi in gates:
        if i==index:selected.update((a,b))
    if not selected:selected={i for i,v in enumerate(models.get(index,()))if v}
    return(index,tuple((i,water[i])for i in sorted(selected)),tuple(v if v in selected else -1 for v in markers))

def conditioned(L,evidence,geometry):
    gates=[]
    for i,a,b,lo,hi in L['gates']:
        ratios=set()
        for r in evidence:
            _,old_a,old_b,old_lo,old_hi=r['gate']
            if old_hi<=old_lo:continue
            ratio=Fraction(r['before'][0][old_a]-old_lo,old_hi-old_lo)
            if r.get('fluid_side')!=geometry['segments'][a]['side']:ratio=1-ratio
            ratios.add(ratio)
        if not ratios:gates.append((i,a,b,lo,hi))
        for ratio in sorted(ratios):
            v=lo+ratio*(hi-lo)
            if v.denominator==1:gates.append((i,a,b,int(v),int(v)))
    return dict(L,gates=gates)
