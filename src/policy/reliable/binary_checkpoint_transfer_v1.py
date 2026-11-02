"""Retrieve an observed persistent tile and plan bounded temporal segments."""
from collections import deque
from binary_contrastive_geometry_v1 import controls,J
from binary_animation_learning_v8 import heading

def retained_checkpoints(trials,values,background):
    rules=[]
    for trial in trials:
        before,after=trial['before'],trial['after']
        if before['levels_completed']!=after['levels_completed']or after['state']!='NOT_FINISHED':continue
        _,_,a=controls(before,values,background);_,_,b=controls(after,values,background)
        if not a or not b or a['actor']['box'][:2]==b['actor']['box'][:2]:continue
        y,x,h,w=b['actor']['box']
        if (h,w)!=tuple(a['actor']['box'][2:]):continue
        patch=[row[x:x+w]for row in before['frame'][y:y+h]]
        if len({v for row in patch for v in row})<2:continue
        rules.append(dict(source=trial['source'],level=before['levels_completed'],patch=patch,
                          observed_start=a['actor'],observed_persistent_actor=b['actor'],
                          source_outcome_was_nonterminal=True,transfer_is_hypothesis=True))
    return rules

def matching_tiles(raw,field,rules,size):
    h,w=size;found={}
    for rule in rules:
        patch=rule['patch']
        if len(patch)!=h or len(patch[0])!=w:continue
        for y in range(field['top']-h+1):
            for x in range(65-w):
                if [row[x:x+w]for row in raw['frame'][y:y+h]]==patch:
                    found[(y,x)]=dict(position=(y,x),rule_source=rule['source'],patch=patch)
    return [found[p]for p in sorted(found)]

def temporal_segments(start,scene,field,models,level,order='field_before_motion'):
    h,w=scene['actor']['box'][2:];moves={}
    for m in models:
        if m.get('retained_level')!=level and any(m['delta']):continue
        if m['before']['box'][2:]!=m['after']['box'][2:]or m['before']['ink']!=m['after']['ink']or m['heading_before']!=m['heading_after']:continue
        dy,dx=m['delta']
        if dy and dx:continue
        moves[tuple(m['word'])]=(dy,dx)
    masks=[set(map(tuple,x))for x in field['blocked']]
    states={tuple(start):dict(program=[],positions=[],motion=0)}
    for step in range(field['slots']):
        nxt={}
        for (y,x),record in states.items():
            for word,(dy,dx)in sorted(moves.items()):
                q=y+dy,x+dx
                if not(0<=q[0]<=field['top']-h and 0<=q[1]<=64-w):continue
                stride=max(abs(dy),abs(dx),1)
                sweep=masks[step+1]if order=='field_before_motion'else masks[step]
                if any((y+dy*k//stride+iy,x+dx*k//stride+ix)in sweep for k in range(1,stride+1)for iy in range(h)for ix in range(w)):continue
                if any((q[0]+iy,q[1]+ix)in masks[step+1]for iy in range(h)for ix in range(w)):continue
                cand=dict(program=record['program']+[word],positions=record['positions']+[q],motion=record['motion']+int(bool(dy or dx)))
                old=nxt.get(q)
                if old is None or(cand['motion'],cand['program'])<(old['motion'],old['program']):nxt[q]=cand
        states=nxt
    return states

def _checkpoint_route(raw,values,background,field,models,rules,outcomes,order):
    pairs,cs,scene=controls(raw,values,background)
    if not scene or len(cs)!=field['slots']or J(scene['goal'])!=J(field['goal']):return None
    actor=scene['actor'];size=tuple(actor['box'][2:]);start=tuple(actor['box'][:2]);goal=tuple(scene['target'])
    if size!=tuple(scene['target_body']['box'][2:])or heading(actor)!=scene['target_heading']or actor['ink']!=scene['target_ink']:return None
    floor=set(scene['floor_inks'])|{actor['ink']}
    gp={(scene['goal']['box'][0]+y,scene['goal']['box'][1]+x)for y,x in scene['goal']['shape']}
    actual={(y,x)for y in range(field['top'])for x in range(64)if raw['frame'][y][x]not in floor and(y,x)not in gp}
    if actual!=set(map(tuple,field['blocked'][0])):return None
    tiles=matching_tiles(raw,field,rules,size)
    nodes={tuple(t['position'])for t in tiles}|{goal};todo=deque([start]);parents={start:None};edges={}
    while todo and goal not in parents:
        at=todo.popleft();reachable=temporal_segments(at,scene,field,models,raw['levels_completed'],order);edges[at]={}
        for destination in sorted(nodes):
            if destination==at or destination not in reachable:continue
            path=reachable[destination]
            if any(J(o['plan']['start'])==J(at)and J(o['plan']['program'])==J(path['program'])and not o['matched']for o in outcomes):continue
            edges[at][destination]=path
            if destination not in parents:parents[destination]=at;todo.append(destination)
    if goal not in parents:return None
    chain=[goal]
    while parents[chain[-1]]is not None:chain.append(parents[chain[-1]])
    chain.reverse();destination=chain[1];path=edges[start][destination]
    return dict(**path,start=start,target=goal,expected_position=destination,scene=scene,
                checkpoint_chain=chain,observed_tile_matches=tiles,field_sources=field['evidence_sources'],
                checkpoint_rule_sources=[r['source']for r in rules],
                intermediate_persistence_is_hypothesis=destination!=goal,prediction_is_unverified=True,
                collision_order_hypothesis=order)

def checkpoint_route(raw,values,background,field,models,rules,outcomes):
    # Frame observations expose command endpoints, not the engine's update order.
    # Prefer the conservative model; test a distinct order only if it has no route.
    plan=_checkpoint_route(raw,values,background,field,models,rules,outcomes,'field_before_motion')
    if plan is not None:return plan
    plan=_checkpoint_route(raw,values,background,field,models,rules,outcomes,'motion_before_field')
    if plan is not None:plan['conservative_temporal_graph_has_no_goal_route']=True
    return plan
