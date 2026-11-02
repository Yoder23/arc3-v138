"""Design a step-off intervention and classify only its observed remote pixels."""


def propose(raw, scene, previous, moves, position, source):
    if previous is None:return None
    before=previous['scene'];a=scene['actor'];n=a['box'][2]
    old=tuple(before['actor']['box'][:2]);dy,dx=old[0]-position[0],old[1]-position[1]
    actions=[a for a,d in moves.items()if tuple(d)==(dy,dx)]
    if not actions:return None
    left=previous['raw']['frame'];right=raw['frame'];ink=left[position[0]+n//2][position[1]+n//2]
    if ink in (scene['floor'],a['ink'],scene['outside']):return None
    bodies=[before['actor'],a,*before.get('other_bodies',[]),*scene.get('other_bodies',[])]
    changed=[]
    for y in range(7,63):
        for x in range(64):
            if left[y][x]==right[y][x] or ink not in (left[y][x],right[y][x]):continue
            if any(o['box'][0]<=y<o['box'][0]+o['box'][2]and o['box'][1]<=x<o['box'][1]+o['box'][3]for o in bodies):continue
            changed.append(dict(y=y,x=x,before=left[y][x],on=right[y][x]))
    if not changed:return None
    return dict(source=source,arrival_source=source-1,control_position=position,expected_off_position=old,
                action=min(actions),changed_remote_pixels=changed,control_ink=ink)


def classify(probe,raw,scene):
    moved=tuple(scene['actor']['box'][:2])==tuple(probe['expected_off_position'])
    values=[raw['frame'][p['y']][p['x']]for p in probe['changed_remote_pixels']]
    if moved and all(v==p['on']for v,p in zip(values,probe['changed_remote_pixels'])):kind='persistent_hypothesis'
    elif moved and all(v==p['before']for v,p in zip(values,probe['changed_remote_pixels'])):kind='momentary_hypothesis'
    else:kind='unresolved'
    return dict(**probe,off_values=values,actual_off_position=scene['actor']['box'][:2],kind=kind,
                scope='One observed step-off intervention; not a universal control law.')
