"""Bounded contact-macro search over literal pixel footprints and learned motion hypotheses."""
import heapq,itertools
from collections import deque
from passive_shape_geometry_v1 import mask

def search(raw,body,objects,goals,motions,allowed,model,max_expansions=4000,forbidden=()):
    if not objects or len(objects)>3 or len(motions)<4:return None
    step={abs(v) for m in motions.values() for v in m['delta'] if v}
    if len(step)!=1:return None
    step=next(iter(step));ds={a:tuple(m['delta']) for a,m in motions.items()};h,w=body['box'][2:];shape=tuple((a,b) for a in range(h) for b in range(w));shapes=[tuple(map(tuple,q['shape'])) for q in objects]
    initial_actor=tuple(body['box'][:2]);initial_positions=tuple(tuple(q['box'][:2]) for q in objects);old_occupied=mask(initial_actor,shape)
    for p,s in zip(initial_positions,shapes):old_occupied|=mask(p,s)
    static=0
    for y,row in enumerate(raw['frame']):
        for x,v in enumerate(row):
            if v not in allowed and not (old_occupied>>(y*64+x))&1:static|=1<<(y*64+x)
    caches={s:{} for s in [shape]+shapes}
    def footprint(p,s):
        cache=caches[s]
        if p not in cache:
            if min(p)<0 or p[0]+max(q[0] for q in s)>=64 or p[1]+max(q[1] for q in s)>=64:cache[p]=None
            else:
                v=mask(p,s);cache[p]=None if v&static else v
        return cache[p]
    actor_positions=[(y,x) for y in range(initial_actor[0]%step,64,step) for x in range(initial_actor[1]%step,64,step) if footprint((y,x),shape) is not None]
    actor_set=set(actor_positions);neighbor={p:{a:(p[0]+d[0],p[1]+d[1]) for a,d in ds.items() if (p[0]+d[0],p[1]+d[1]) in actor_set} for p in actor_positions}
    targets=[]
    for s in shapes:
        gs=[tuple(g['interior']['box'][:2]) for g in goals if tuple(map(tuple,g['interior']['shape']))==s]
        if not gs:return None
        targets.append(gs)
    assignments=[q for q in itertools.product(*targets) if len(set(q))==len(q)]
    if not assignments:return None
    def heuristic(ps):return min(sum(((p[0]!=q[0])+(p[1]!=q[1])) if model=='slide' else (abs(p[0]-q[0])+abs(p[1]-q[1]))/step for p,q in zip(ps,goal)) for goal in assignments)
    initial=(initial_positions,initial_actor);cost={initial:0};parent={initial:None};heap=[(heuristic(initial_positions),0,0,initial)];serial=expanded=0;regions=set()
    while heap and expanded<max_expansions:
        _,ng,_,state=heapq.heappop(heap);g=-ng
        if cost[state]!=g:continue
        ps,actor=state;expanded+=1;object_masks=[footprint(p,s) for p,s in zip(ps,shapes)]
        if any(q is None for q in object_masks):continue
        occupied=0
        for q in object_masks:occupied|=q
        todo=deque([actor]);routes={actor:[]}
        while todo:
            at=todo.popleft()
            for a,q in neighbor.get(at,{}).items():
                if (ps,at,a) not in forbidden and q not in routes and not footprint(q,shape)&occupied:routes[q]=routes[at]+[a];todo.append(q)
        region=(ps,min(routes))
        if region in regions:continue
        regions.add(region)
        if ps in assignments:
            final_goals=[(g['box'][0]+1,g['box'][1]+1) for g in raw.get('_actor_goals',[]) if tuple(g['box'][2:])==(h+2,w+2)]
            reachable=[q for q in final_goals if q in routes]
            if reachable:
                tail=routes[min(reachable,key=lambda p:(len(routes[p]),p))];segments=[];cursor=state
                while parent[cursor] is not None:prev,route=parent[cursor];segments.append(route);cursor=prev
                moves=[a for seg in reversed(segments) for a in seg]+tail
                return dict(actions=moves,expanded=expanded,model=model,initial_positions=initial_positions,goal_assignment=ps)
        for i,p in enumerate(ps):
            others=occupied^object_masks[i]
            for a,d in sorted(ds.items()):
                contacts=[]
                for at,route in routes.items():
                    q=neighbor.get(at,{}).get(a)
                    if (ps,at,a) not in forbidden and q is not None and footprint(q,shape)&object_masks[i] and not footprint(q,shape)&others:contacts.append((len(route),at,route))
                if not contacts:continue
                for _,at,route in sorted(contacts)[:2]:
                    dest=p;actor_mask=footprint(at,shape)
                    for _ in range(64//step):
                        q=(dest[0]+d[0],dest[1]+d[1]);v=footprint(q,shapes[i])
                        if v is None or v&(others|actor_mask):break
                        dest=q
                        if model=='step' or model.startswith('fixed:') and _+1>=int(model.split(':')[1]):break
                    if dest==p:continue
                    new=list(ps);new[i]=dest;key=(tuple(new),at);gg=g+1+len(route)/100
                    if gg>=cost.get(key,10**9):continue
                    cost[key]=gg;parent[key]=(state,route+[a]);serial+=1;heapq.heappush(heap,(gg+4*heuristic(key[0]),-gg,serial,key))
    return None
