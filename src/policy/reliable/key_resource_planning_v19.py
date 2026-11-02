"""Learn a visible expendable meter and compose symbol changes with replenishment."""
from collections import deque
from functools import lru_cache
from conditional_goal_motion_v1 import relaxed,resolve
from key_planning_feasibility_v1 import possible
from math import lcm
from key_control_clock_v1 import at as control_at
from binary_demonstration_bootstrap_v1 import components
def discover(frame,scene):
    candidates=[]
    for o in components(frame):
        y,x,h,w=o['box']
        if len(o['shape'])==h*w and 1<=min(h,w)<=3 and max(h,w)>=20 and min(y,x,64-y-h,64-x-w)<=3 and o['ink']not in(*scene['identity'],scene['floor']):candidates.append(o)
    if not candidates:return None
    o=max(candidates,key=lambda v:len(v['shape']));return dict(box=o['box'],ink=o['ink'],capacity=len(o['shape']))
def value(frame,meter):
    y,x,h,w=meter['box'];return sum(frame[yy][xx]==meter['ink']for yy in range(y,y+h)for xx in range(x,x+w))
def search(scene,mask,controls,rules,shape_rules,color_rules,resource_rules,consumed,meter,remaining,cost,motion=None,clocks=None,t=0,limit=100000,goal_contact=True,stationary_rejected=False):
    motion=motion or {};clocks=clocks or {};period=lcm(*[m['period']for m in clocks.values()])if clocks else 1
    from key_glyph_learning_v20 import covers,transform,DIRS
    n=scene['actor'][2];startpos=scene['actor'][:2];goal=scene['goal'];target=(goal[0]+(goal[2]-n)//2,goal[1]+(goal[3]-n)//2)
    goals=scene.get('conditional_goal_regions',[])
    if not possible(scene,mask,controls,rules,shape_rules,color_rules,relaxed(motion,goals),clocks,goal_contact,covers,transform,DIRS):return None
    capacity=meter['capacity']//cost;energy=remaining//cost;used=sum(1<<i for i,c in enumerate(controls)if c['box']in consumed);start=(startpos,scene['key'],scene['key_color'],energy,used,t%period);queue=deque([(start,[])]);seen={start};best={(startpos,scene['key'],scene['key_color'],used,t%period):energy};expanded=0
    @lru_cache(None)
    def valid(q):return all((y,x)in mask for y in range(q[0],q[0]+n)for x in range(q[1],q[1]+n))
    @lru_cache(None)
    def transition(p,action,key,color):
        q=resolve(motion,p,action,n,key,color,goals)
        return q if valid(q)else p if clocks else None
    @lru_cache(None)
    def entered(p,q,phase):return tuple((i,c['signature'])for i,c in enumerate(controls)if covers(q,n,control_at(c,clocks,phase+1))and not covers(p,n,control_at(c,clocks,phase)))
    while queue and expanded<limit:
        (p,key,color,energy,used,phase),path=queue.popleft();expanded+=1
        if (p==target or not goal_contact)and key==scene['target']and color==scene['target_color']:return path
        if energy<=0:continue
        for action,(dy,dx)in DIRS.items():
            q=transition(p,action,key,color)
            if q is None:continue
            if stationary_rejected and q==p:continue
            newkey=key;newcolor=color;newenergy=energy-1;newused=used
            for i,sig in entered(p,q,phase):
                if sig in resource_rules and not used&(1<<i):newenergy=capacity;newused|=1<<i
                newcolor=color_rules.get(sig,{}).get(newcolor,newcolor)
                operations=rules.get(sig)
                newkey=shape_rules.get(sig,{}).get(newkey,transform(newkey,min(operations)if operations else 0))
            state=(q,newkey,newcolor,newenergy,newused,(phase+1)%period)
            context=(q,newkey,newcolor,newused,(phase+1)%period)
            if state not in seen and newenergy>best.get(context,-1):
                best[context]=newenergy;seen.add(state);queue.append((state,path+[action]))
    return None
