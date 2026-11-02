"""Learn within-program field changes from repeated, stationary observations."""
from binary_contrastive_geometry_v1 import controls,execution_effects,J
from binary_animation_learning_v8 import heading

def field_model(trials, values, background):
    examples=[];reference=None
    for trial in trials:
        pairs,cs,scene=controls(trial['before'],values,background)
        if not scene or trial['before']['levels_completed']!=trial['after']['levels_completed']:
            continue
        effects=execution_effects(trial,values,background)
        if len(effects)!=len(cs) or any(m['before']!=m['after'] for m in effects):
            continue
        top=min(a['box'][0]for a,b in pairs)
        floor=set(scene['floor_inks'])|{scene['actor']['ink']}
        goal={(scene['goal']['box'][0]+y,scene['goal']['box'][1]+x)for y,x in scene['goal']['shape']}
        masks=[]
        for frame in trial['after']['animation_frames']:
            masks.append([[y,x]for y in range(top)for x in range(64)if frame[y][x]not in floor and(y,x)not in goal])
        signature=dict(blocked=masks,top=top,slots=len(cs),goal=scene['goal'],floor_inks=scene['floor_inks'],actor_ink=scene['actor']['ink'])
        if reference is None:reference=signature
        if J(signature)!=J(reference):continue
        examples.append(trial['source'])
    if len(examples)<2 or reference is None or all(m==reference['blocked'][0]for m in reference['blocked']):
        return None
    return dict(reference,evidence_sources=examples,phase_reset_is_hypothesis=True,
                scope='Repeated stationary executions agree on these visible within-program obstruction masks; movement interactions and intermediate persistence still need testing.')

def plan_temporal(raw, values, background, model, known_models, outcomes):
    pairs,cs,scene=controls(raw,values,background)
    if not scene or len(cs)!=model['slots'] or J(scene['goal'])!=J(model['goal']):return None
    actor=scene['actor'];h,w=actor['box'][2:];start=tuple(actor['box'][:2]);goal=tuple(scene['target'])
    if tuple(scene['target_body']['box'][2:])!=(h,w) or heading(actor)!=scene['target_heading'] or actor['ink']!=scene['target_ink']:return None
    moves={}
    for m in known_models:
        if m.get('retained_level')!=raw['levels_completed'] and any(m['delta']):continue
        if m['before']['box'][2:]!=m['after']['box'][2:]or m['before']['ink']!=m['after']['ink']or m['heading_before']!=m['heading_after']:continue
        dy,dx=m['delta']
        if dy and dx:continue
        moves[tuple(m['word'])]=(dy,dx)
    if not any(delta==(0,0)for delta in moves.values()):return None
    blocked=[set(map(tuple,mask))for mask in model['blocked']]
    floor=set(scene['floor_inks'])|{actor['ink']}
    goal_pixels={(scene['goal']['box'][0]+y,scene['goal']['box'][1]+x)for y,x in scene['goal']['shape']}
    actual={(y,x)for y in range(model['top'])for x in range(64)if raw['frame'][y][x]not in floor and(y,x)not in goal_pixels}
    if actual!=blocked[0]:return None
    states={start:dict(program=[],positions=[],motion=0)};examined=0
    for step in range(model['slots']):
        nxt={}
        for (y,x),record in states.items():
            for word,(dy,dx)in sorted(moves.items()):
                yy,xx=y+dy,x+dx
                if not(0<=yy<=model['top']-h and 0<=xx<=64-w):continue
                stride=max(abs(dy),abs(dx),1)
                if any((y+dy*k//stride+iy,x+dx*k//stride+ix)in blocked[step+1] for k in range(1,stride+1)for iy in range(h)for ix in range(w)):continue
                candidate=dict(program=record['program']+[word],positions=record['positions']+[(yy,xx)],motion=record['motion']+int(bool(dy or dx)))
                old=nxt.get((yy,xx));examined+=1
                if old is None or(candidate['motion'],candidate['program'])<(old['motion'],old['program']):nxt[(yy,xx)]=candidate
        states=nxt
    distance=lambda p:abs(p[0]-goal[0])+abs(p[1]-goal[1])
    choices=[]
    for destination,record in states.items():
        if distance(destination)>=distance(start):continue
        if any(J(o['plan']['start'])==J(start)and J(o['plan']['program'])==J(record['program'])for o in outcomes):continue
        choices.append((distance(destination),record['motion'],record['program'],destination,record))
    if not choices:return None
    _,_,_,destination,record=min(choices)
    return dict(**record,start=start,target=goal,expected_position=destination,scene=scene,
                field_sources=model['evidence_sources'],examined_transitions=examined,
                intermediate_persistence_is_hypothesis=destination!=goal,
                prediction_is_unverified=True)
