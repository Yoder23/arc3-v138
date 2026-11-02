"""A bounded directed contact experiment after several controlled bodies reach tentative goals."""
import copy
from collections import deque
from selectable_passive_planner_v9 import Agent as Base
from visible_passive_components_v1 import components
from passive_shape_geometry_v1 import enclosed
from selectable_rect_core_v1 import inside
class Agent(Base):
    def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self.multi_passive_probe=None
    def reset_level(self,raw):super().reset_level(raw);self.multi_passive_probe=None
    def observe(self,raw):
        r=super().observe(raw)
        if 2<=len(self.objects)<=4 and not self.shape_goals:
            shapes={tuple(map(tuple,q['shape'])) for q in self.candidates(raw)}
            for outline in components(raw['frame']):
                if outline['ink'] not in {g['ink'] for g in self.goals}:continue
                interior=enclosed(outline)
                if interior and tuple(interior['shape']) in shapes:self.shape_goals.append(dict(outline=copy.deepcopy(outline),interior=interior,observed_at=self.t,goal_is_hypothesis=True))
        return r
    def directed_contact(self,raw,body,target,action):
        cells={(target['box'][0]+y,target['box'][1]+x) for y,x in target['shape']};h,w=body['box'][2:];start=tuple(body['box'][:2]);todo=deque([start]);parents={start:None};allowed=self.allowed()
        while todo:
            at=todo.popleft()
            for a,m in sorted(self.motions.items()):
                dy,dx=m['delta'];q=(at[0]+dy,at[1]+dx)
                if not(0<=q[0]<=64-h and 0<=q[1]<=64-w):continue
                pixels={(y,x) for y in range(q[0],q[0]+h) for x in range(q[1],q[1]+w)}
                if pixels&cells:
                    if a!=action:continue
                    path=[a];cursor=at
                    while parents[cursor] is not None:prev,act=parents[cursor];path.append(act);cursor=prev
                    return path[::-1]
                if q in parents or any(not inside((y,x),body['box']) and raw['frame'][y][x] not in allowed for y,x in pixels):continue
                parents[q]=(at,a);todo.append(q)
        return None
    def respond(self,raw):
        if self.multi_passive_probe is None:
            r=super().respond(raw)
            if not r['done'] or raw['state']!='NOT_FINISHED' or not(2<=len(self.objects)<=4) or not self.motions:return r
            body=next((b for b in self.objects if tuple(b['box'])==tuple(self.active_box or ())),None)
            if not body:return r
            choices=[]
            for target in self.candidates(raw):
                for goal in self.shape_goals:
                    if tuple(map(tuple,target['shape']))!=tuple(map(tuple,goal['interior']['shape'])):continue
                    gap=tuple(goal['interior']['box'][i]-target['box'][i] for i in (0,1))
                    for a,m in self.motions.items():
                        progress=sum(d*g for d,g in zip(m['delta'],gap))
                        if progress<=0:continue
                        route=self.directed_contact(raw,body,target,a)
                        if route:choices.append((-progress,len(route),tuple(target['box']),a,target,goal))
            if not choices:return r
            _,_,_,a,target,goal=min(choices,key=lambda q:q[:4]);self.multi_passive_probe=dict(target=copy.deepcopy(target),goal=copy.deepcopy(goal),action=a,steps=0,contact=None)
        else:
            if raw['state']!='NOT_FINISHED' or self.level!=raw['levels_completed']:self.multi_passive_probe=None;return super().respond(raw)
            self.observe(raw)
        state=self.multi_passive_probe
        if state['contact']:
            p=state['contact']
            if not p.get('processed'):
                p['processed']=True;before=p['target'];before_positions={tuple(q['box']) for q in p['candidates'] if q['ink']==before['ink']};now=[q for q in self.candidates(raw) if q['ink']==before['ink'] and q['shape']==before['shape'] and tuple(q['box']) not in before_positions]
                if len(now)==1:
                    after=now[0];delta=tuple(after['box'][i]-before['box'][i] for i in (0,1));actor=next((b for b in self.objects if tuple(b['box'])==tuple(p['actor']['box'])),None)
                    if (delta[0]==0)!=(delta[1]==0):self.learned_passive_effects.append(dict(source=p['source'],action=p['action'],before=before,after=copy.deepcopy(after),delta=delta,actor_before=p['actor'],actor_after=copy.deepcopy(actor),outcome='observed_other_component_translation',causality_is_hypothesis=True))
            return dict(done=True,action=None,data={},learned_passive_effects=copy.deepcopy(self.learned_passive_effects),multi_passive_contact_source=p['source'])
        body=next((b for b in self.objects if tuple(b['box'])==tuple(self.active_box or ())),None)
        if not body or state['steps']>=64:return dict(done=True,action=None,data={})
        route=self.directed_contact(raw,body,state['target'],state['action'])
        if not route:return dict(done=True,action=None,data={})
        if len(route)==1:state['contact']=dict(source=self.t,action=route[0],target=copy.deepcopy(state['target']),actor=copy.deepcopy(body),candidates=copy.deepcopy(self.candidates(raw)))
        r=self.answer(raw,route[0],{},'test_multi_actor_passive_contact' if len(route)==1 else 'approach_multi_actor_passive_contact',body,route);state['steps']+=1
        r['certificate']['passive_contact_hypothesis']=dict(target=copy.deepcopy(state['target']),route=route,interaction_unconfirmed=True)
        r['certificate']['multi_passive_goal_hypothesis']=copy.deepcopy(state['goal']);return r
