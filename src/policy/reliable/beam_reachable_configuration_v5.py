"""Require a feasible sequence of observed-size movements before accepting a layout."""
def reachable(scene,target,groups):
    from beam_split_learner_v20 import move_route
    scene=dict(scene,bars=[dict(b,box=tuple(b['box']))for b in scene['bars']]);pending={g[0]for g in groups};poses=tuple(b['box'][:2]for b in scene['bars'])
    while pending:
        progressed=False
        for i in sorted(pending):
            group=next(g for g in groups if i in g)
            if poses[i]==target[i]:pending.remove(i);progressed=True;break
            path=move_route(scene,i,target[i],set(),groups)
            if path is None:continue
            delta=target[i][0]-poses[i][0],target[i][1]-poses[i][1]
            for j in group:
                box=scene['bars'][j]['box'];scene['bars'][j]['box']=(box[0]+delta[0],box[1]+delta[1],*box[2:])
            poses=tuple(b['box'][:2]for b in scene['bars']);pending.remove(i);progressed=True;break
        if not progressed:return False
    return poses==target
