"""Three complete frame sides support a tentative goal behind a fourth-side occluder."""
from passive_shape_geometry_v1 import components

def goals(frame,body):
    h,w=body['box'][2:];out=[]
    for c in components(frame):
        y,x,hh,ww=c['box'];ink=c['ink']
        if (hh,ww)!=(h+2,w+2) or ink==body['ink']:continue
        edges={'top':[(0,b) for b in range(ww)],'bottom':[(hh-1,b) for b in range(ww)],'left':[(a,0) for a in range(hh)],'right':[(a,ww-1) for a in range(hh)]}
        complete=[k for k,ps in edges.items() if all(frame[y+a][x+b]==ink for a,b in ps)]
        if len(complete)!=3:continue
        side=next(k for k in edges if k not in complete);missing=[(a,b,frame[y+a][x+b]) for a,b in edges[side] if frame[y+a][x+b]!=ink]
        center=frame[y+hh//2][x+ww//2]
        if not missing or center==ink or any(frame[y+a][x+b]!=center for a in range(1,hh-1) for b in range(1,ww-1)):continue
        if any(v in (ink,center) for a,b,v in missing):continue
        out.append(dict(box=(y,x,hh,ww),ink=ink,center=center,fragmentary_goal=True,complete_sides=complete,occluded_side=side,observed_occluder_pixels=missing,goal_is_hypothesis=True))
    return out
