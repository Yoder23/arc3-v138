"""Learn click-controlled endpoints and test a relational midpoint goal from legal pixels."""
import copy
from collections import Counter
from structured_interaction_probe_v1 import parts
from visual_transform_learner import digest

def scene(obs):
    f=obs['frame'];ps=parts(f);ends={};middle=[];goals=[]
    for p in ps:
        if p['h']==p['w']==5 and p['area']==12:ends[p['color']]=(p['y']+2,p['x']+2)
        if p['h']==p['w']==5 and p['area']==20:middle.append((p['color'],(p['y']+2,p['x']+2)))
    colors={c for c,_ in middle}
    for c in colors:
        points={(p['y'],p['x']) for p in ps if p['color']==c and p['area']==1}
        while points:
            group={min(points)};queue=list(group);points-=group
            while queue:
                y,x=queue.pop();near={p for p in points if max(abs(p[0]-y),abs(p[1]-x))<=2};points-=near;group|=near;queue.extend(near)
            ys=[p[0] for p in group];xs=[p[1] for p in group]
            if len(group)>=8 and max(ys)-min(ys)==max(xs)-min(xs) and 4<=max(ys)-min(ys)<=10:
                goals.append(dict(color=c,center=((min(ys)+max(ys))//2,(min(xs)+max(xs))//2),points=sorted(group)))
    return ends,middle,goals

class Agent:
    def __init__(self):
        self.previous=None;self.last=None;self.history={};self.motion=[];self.swaps=[];self.active=None;self.level=None;self.goals=[];self.goal_source=None;self.probes=0;self.pending_swap=False;self.failures=[];self.goal_outcomes=[];self.steps=0
    def observe(self,obs):
        if self.previous is None:return
        e=dict(before=self.previous,action=self.last['action'],data=self.last['data'],after=copy.deepcopy(obs));h=digest(e);self.history[h]=e
        if obs['levels_completed']>self.previous['levels_completed'] or obs['state']=='WIN':self.goal_outcomes.append(dict(source=h,progress=True));return
        if self.last['action']==0:return
        before,mb,_=scene(self.previous);after,ma,_=scene(obs);changed=[c for c in sorted(before.keys()&after.keys()) if before[c]!=after[c]];p=(self.last['data']['y'],self.last['data']['x'])
        if len(changed)==1 and len(before)==len(after)==2 and after[changed[0]]==p and len(ma)==1:
            active=changed[0];passive=next(c for c in after if c!=active);mid=ma[0][1]
            if mid==tuple((after[active][i]+after[passive][i])//2 for i in (0,1)):
                self.active=active;self.motion.append(dict(source=h,active=active,passive=passive,origin=before[active],destination=after[active],fixed=after[passive],midpoint=mid,midpoint_color=ma[0][0]));self.probes+=1
        elif len(changed)==2 and set(before.values())==set(after.values()):
            self.swaps.append(dict(source=h,before=before,after=after,click=p));self.pending_swap=False
        elif before==after and self.last.get('certificate',{}).get('reason')=='test_relational_goal':
            self.failures.append(dict(source=h,click=p,goal=self.last['certificate']['goal']))
    def respond(self,obs):
        self.observe(obs);ends,middle,goals=scene(obs);self.steps+=1
        if self.level!=obs['levels_completed']:
            self.level=obs['levels_completed'];self.goals=copy.deepcopy(goals);self.goal_source=digest(obs);self.pending_swap=False;self.probes=0
        c=dict(kind='midpoint_relational_plan',context=digest(obs),goal_is_hypothesis=True,goal_source=self.goal_source,goals=copy.deepcopy(self.goals),motion=copy.deepcopy(self.motion),swaps=copy.deepcopy(self.swaps),goal_outcomes=copy.deepcopy(self.goal_outcomes),failures=copy.deepcopy(self.failures));p=None;reason='unresolved_midpoint_scene';action=6
        f=obs['frame'];bg=Counter(v for row in f for v in row).most_common(1)[0][0]
        def legal(p):return 3<=p[0]<61 and 3<=p[1]<61 and f[p[0]][p[1]]==bg
        if obs['state']=='GAME_OVER':action=0;reason='reset_after_actual_failure'
        elif obs['state']=='WIN':action=None;reason='WIN'
        elif len(ends)==2 and self.goals:
            g=tuple(self.goals[0]['center']);c['goal']=g
            if self.probes<2 or self.active not in ends:
                offsets=[(-8,0),(0,-8),(8,0),(0,8),(-12,-12),(12,12)]
                choices=[(g[0]+dy,g[1]+dx) for dy,dx in offsets]
                candidates=[q for q in choices if legal(q) and all(max(abs(q[i]-e[i]) for i in (0,1))>4 for e in ends.values())]
                if candidates:p=candidates[self.probes%len(candidates)];reason='probe_endpoint_control'
            else:
                passive=next(v for k,v in ends.items() if k!=self.active);active=ends[self.active];reflected=tuple(2*g[i]-passive[i] for i in (0,1));c.update(active=self.active,endpoints=ends,reflected=reflected)
                if legal(reflected) and max(abs(reflected[i]-passive[i]) for i in (0,1))>4:p=reflected;reason='test_relational_goal'
                else:
                    candidates=[(g[0]+dy,g[1]+dx) for dy,dx in [(-6,0),(0,-6),(6,0),(0,6),(-9,0),(0,-9)]]
                    stage=next((q for q in candidates if (legal(q) or q==active) and legal(tuple(2*g[i]-q[i] for i in (0,1)))),None)
                    if stage is not None:
                        if active==stage:p=passive;reason='probe_endpoint_selection';self.pending_swap=True
                        else:p=stage;reason='stage_endpoint_for_feasible_reflection'
        if p is None and action==6:
            # A bounded diagnostic stop avoids repeating an unresolved hypothesis indefinitely.
            action=None
        c['reason']=reason;c['click']=p;c['action']=action
        response=dict(action=action,data={} if p is None else dict(x=p[1],y=p[0]),done=action is None,certificate=c if action==6 else None,advisor='midpoint_relational_learner',diagnostics=dict(reason=reason,retained_transitions=len(self.history),motion_evidence=len(self.motion),selection_evidence=len(self.swaps),goal_outcomes=copy.deepcopy(self.goal_outcomes)))
        self.previous=copy.deepcopy(obs);self.last=copy.deepcopy(response);return response
