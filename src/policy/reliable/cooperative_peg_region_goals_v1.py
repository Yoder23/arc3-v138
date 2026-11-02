"""Propose unexplored static regions using registered, observed ordinary-token visits."""
from cooperative_peg_perception_v5 import view

def propose(raw, current, outcomes, rule, carrier_ink):
    level=raw['levels_completed']; visited=set(); sources=[]
    for event in outcomes:
        if event['before']['levels_completed']!=level:
            continue
        before=view(event['before'],rule,carrier_ink)
        if before:visited.update(map(tuple,before['ordinary']))
        if event['after']['levels_completed']!=level:
            visited.clear();sources.clear();continue
        delta=event.get('registration',{}).get('delta',(0,0))
        visited={tuple(p[j]-delta[j]for j in(0,1))for p in visited}
        after=event.get('view_after')
        if after:visited.update(map(tuple,after['ordinary']))
        sources.append(event['source'])
    visited.update(map(tuple,current['ordinary']))
    remaining=set(map(tuple,current['scene']['cells']));pitch=current['scene']['pitch'];regions=[]
    while remaining:
        seed=min(remaining);region={seed};pending=[seed];remaining.remove(seed)
        while pending:
            p=pending.pop()
            neighbors={q for q in remaining if abs(p[0]-q[0])+abs(p[1]-q[1])==pitch}
            remaining-=neighbors;region|=neighbors;pending.extend(sorted(neighbors))
        regions.append(sorted(region))
    novel=[r for r in regions if not set(r)&visited]
    return dict(level=level,outcome_sources=sources,registered_visits=sorted(visited),regions=regions,goals=sorted({p for r in novel for p in r}),hypothesis='reach_an_unvisited_static_region_when_local_completion_and_joint_loading_goals_fail')
