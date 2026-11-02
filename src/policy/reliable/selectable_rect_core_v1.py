"""Select, observe, and plan over multiple visible bodies and tentative goals."""
from collections import Counter,deque
import copy
from selectable_rect_geometry_v1 import rings,actor_group,body_crop

def same(a,b):return a['box']==b['box'] and a['ink']==b['ink']
def inside(p,box):return box[0]<=p[0]<box[0]+box[2] and box[1]<=p[1]<box[1]+box[3]
class Agent:
    def __init__(self,prior=None):
        self.prior=prior;self.active=False;self.t=0;self.level=None;self.previous=None;self.palette=None;self.size=None;self.objects=[];self.goals=[];self.motions={};self.motion_memory=[];self.failures=[];self.selections=[];self.episodes=[];self.active_box=None;self.active_center=None;self.floor=None;self.queries=Counter();self.disable_selection=False;self.goal_visits=[];self.extra_terrain=set();self.disable_terrain_probe=False
    def reset_level(self,raw):
        if self.level is not None:self.episodes.append(dict(level=self.level,motions=copy.deepcopy(self.motions),failures=copy.deepcopy(self.failures),selections=copy.deepcopy(self.selections),goal_visits=copy.deepcopy(self.goal_visits),progress_observed=raw['levels_completed']>self.level))
        self.level=raw['levels_completed'];self.previous=None;self.palette=None;self.size=None;self.objects=[];self.goals=[];self.motions={};self.failures=[];self.selections=[];self.active_box=None;self.active_center=None;self.floor=None;self.queries=Counter();self.goal_visits=[]
    def detect_objects(self,raw):
        current=[r for r in rings(raw['frame']) if r['ink']==self.palette and r.get('tile_body')]
        old=self.previous
        if not old or old['raw']['levels_completed']!=raw['levels_completed']:return current
        for b in old['objects']:
            if any(same(b,q) for q in current):continue
            h,w=b['box'][2:];motion=self.motions.get(old['action']);moving=tuple(b['box'])==tuple(self.active_box or ())
            deltas=[tuple(motion['delta']),(0,0)] if motion and moving else [(0,0)]
            if moving and old['action'] in (1,2,3,4) and not motion:
                steps={abs(v) for m in self.motions.values() for v in m['delta'] if v};deltas=sorted({(0,0)}|{q for n in steps for q in ((n,0),(-n,0),(0,n),(0,-n))})
            if any(tuple(q['box'][:2])==(b['box'][0]+dy,b['box'][1]+dx) for dy,dx in deltas for q in current if not any(same(q,o) for o in old['objects'] if o is not b)):continue
            options=[]
            for delta in dict.fromkeys(deltas):
                y=b['box'][0]+delta[0];x=b['box'][1]+delta[1]
                if not(0<=y<=64-h and 0<=x<=64-w):continue
                if any(tuple(o['box'])==(y,x,h,w) and all(old['raw']['frame'][yy][xx]==raw['frame'][yy][xx] for yy in range(y,y+h) for xx in range(x,x+w)) for o in old['objects'] if o is not b):continue
                q=body_crop(raw['frame'],(y,x,h,w),self.palette,True)
                if q:
                    q['partial_crop_support']=dict(source=old['source'],before=copy.deepcopy(b),delta=delta,hypothesis='rectangular_body_at_observed_motion_or_stationary_prediction');options.append(q)
            if len(options)==1:current.append(options[0])
        return current
    def observe(self,raw):
        if self.palette is None:
            candidates=actor_group(raw['frame'])
            if not candidates:return False
            self.palette=candidates[0]['ink'];self.size=candidates[0]['box'][2]
        current=self.detect_objects(raw)
        if not current:return False
        old=self.previous
        if old and old['raw']['levels_completed']==self.level:
            before=old['objects'];removed=[r for r in before if not any(same(r,q) for q in current)];added=[q for q in current if not any(same(r,q) for r in before)]
            if old['action'] in (1,2,3,4) and len(removed)==len(added)==1:
                b,q=removed[0],added[0];delta=tuple(q['box'][i]-b['box'][i] for i in (0,1))
                if (delta[0]==0)!=(delta[1]==0) and b['box'][2:]==q['box'][2:]:
                    m=dict(source=old['source'],action=old['action'],before=copy.deepcopy(b),after=copy.deepcopy(q),delta=delta)
                    self.motions[old['action']]=m;self.motion_memory.append(m);self.active_box=q['box'];self.active_center=q['center']
                    vacated=[raw['frame'][y][x] for y in range(b['box'][0],b['box'][0]+b['box'][2]) for x in range(b['box'][1],b['box'][1]+b['box'][3]) if not inside((y,x),q['box'])]
                    if vacated:self.floor=Counter(vacated).most_common(1)[0][0]
            elif old['action'] in self.motions and self.active_box and any(tuple(q['box'])==tuple(self.active_box) for q in current):
                body=next(q for q in current if tuple(q['box'])==tuple(self.active_box));dy,dx=self.motions[old['action']]['delta'];dest=(body['box'][0]+dy,body['box'][1]+dx)
                self.failures.append(dict(source=old['source'],action=old['action'],body=copy.deepcopy(body),destination=dest,context=self.context(old['raw'],dest,before,body),outcome='no_observed_displacement',causality='context_bound_observation'))
            if old['action']==6 and old.get('target'):
                q=next((q for q in current if same(q,old['target'])),None)
                if q:
                    self.active_box=q['box'];self.selections.append(dict(source=old['source'],target=copy.deepcopy(old['target']),after=copy.deepcopy(q),hypothesis='clicked_object_may_be_active',confirmed_by_motion=False))
        self.objects=current
        if self.floor is not None and not self.goals:
            bg=Counter(v for row in raw['frame'] for v in row).most_common(1)[0][0]
            gs=[r for r in rings(raw['frame']) if any(tuple(r['box'][2:])==(o['box'][2]+2,o['box'][3]+2) for o in current) and r['ink'] not in (self.palette,self.floor,bg) and r['center']==self.floor]
            if 1<=len(gs)<=len(current):self.goals=[dict(g,observed_at=self.t) for g in gs]
        for q in current:
            for g in self.goals:
                if tuple(q['box'][:2])==(g['box'][0]+1,g['box'][1]+1) and not any(v['goal']['box']==g['box'] for v in self.goal_visits):self.goal_visits.append(dict(source=self.t,body=copy.deepcopy(q),goal=copy.deepcopy(g),outcome='observed_goal_hypothesis_contact',task_success_confirmed=False))
        return True
    def context(self,raw,dest,objects,body):
        y,x=dest;h,w=body['box'][2:]
        values=[raw['frame'][a][b] if 0<=a<64 and 0<=b<64 else -1 for a in range(y,y+h) for b in range(x,x+w)]
        return (tuple(values),tuple(sorted(tuple(q['box']) for q in objects if not same(q,body))))
    def route(self,raw,body,goal):
        start=tuple(body['box'][:2]);target=(goal['box'][0]+1,goal['box'][1]+1);h,w=body['box'][2:];others=[q for q in self.objects if not same(q,body)];allowed={self.floor}|{g['ink'] for g in self.goals}|self.extra_terrain
        todo=deque([start]);parents={start:None}
        while todo:
            at=todo.popleft()
            if at==target:
                route=[]
                while parents[at] is not None:prev,a=parents[at];route.append(a);at=prev
                return route[::-1]
            for a,m in sorted(self.motions.items()):
                dy,dx=m['delta'];q=(at[0]+dy,at[1]+dx)
                if q in parents or not(0<=q[0]<=64-h and 0<=q[1]<=64-w):continue
                if any(inside((y,x),o['box']) for y in range(q[0],q[0]+h) for x in range(q[1],q[1]+w) for o in others):continue
                if any(not inside((y,x),body['box']) and raw['frame'][y][x] not in allowed for y in range(q[0],q[0]+h) for x in range(q[1],q[1]+w)):continue
                context=self.context(raw,q,self.objects,body)
                if any(f['action']==a and tuple(f['body']['box'][:2])==at and f['context']==context for f in self.failures):continue
                parents[q]=(at,a);todo.append(q)
        return None
    def answer(self,raw,a,d,tag,target=None,route=None,goal=None):
        c=dict(kind='selectable_multi_object_planning',observed_at=self.t,tag=tag,objects=copy.deepcopy(self.objects),goals=copy.deepcopy(self.goals),motions=copy.deepcopy(self.motions),failures=copy.deepcopy(self.failures),selections=copy.deepcopy(self.selections),active_box=self.active_box,active_is_hypothesis=True,target=copy.deepcopy(target),route=route or [],goal=copy.deepcopy(goal),goals_are_hypotheses=True,terrain_probe=sorted(self.extra_terrain),terrain_is_hypothesis=True)
        self.previous=dict(raw=copy.deepcopy(raw),source=self.t,action=a,data=copy.deepcopy(d),objects=copy.deepcopy(self.objects),target=copy.deepcopy(target));self.t+=1;self.queries[a]+=1;self.active=True
        return dict(done=False,action=a,data=d,certificate=c)
    def respond(self,raw):
        assert set(raw)=={'frame','state','available_actions','levels_completed'}
        if raw['state']!='NOT_FINISHED':return dict(done=True,action=None,data={})
        if self.level!=raw['levels_completed']:self.reset_level(raw)
        if not self.observe(raw):return dict(done=True,action=None,data={})
        controls=[a for a in (1,2,3,4) if a in raw['available_actions']]
        unknown=[a for a in controls if self.queries[a]==0]
        if unknown:return self.answer(raw,unknown[0],{},'learn_control')
        self.extra_terrain=set()
        occupied={tuple(q['box'][:2]) for q in self.objects};choices=[]
        for body in self.objects:
            if any(tuple(body['box'][:2])==(g['box'][0]+1,g['box'][1]+1) for g in self.goals):continue
            if self.disable_selection and tuple(body['box'])!=tuple(self.active_box or ()):continue
            for goal in self.goals:
                if tuple(goal['box'][2:])!=(body['box'][2]+2,body['box'][3]+2):continue
                if (goal['box'][0]+1,goal['box'][1]+1) in occupied:continue
                route=self.route(raw,body,goal)
                if route:choices.append((len(route)+(tuple(body['box'])!=tuple(self.active_box or ())),tuple(body['box']),body,goal,route))
        if not choices and not self.disable_terrain_probe:
            bg=Counter(v for row in raw['frame'] for v in row).most_common(1)[0][0]
            self.extra_terrain=set(v for row in raw['frame'] for v in row)-{bg,self.palette}
            occupied={tuple(q['box'][:2]) for q in self.objects};choices=[]
            for body in self.objects:
                if any(tuple(body['box'][:2])==(g['box'][0]+1,g['box'][1]+1) for g in self.goals):continue
                if self.disable_selection and tuple(body['box'])!=tuple(self.active_box or ()):continue
                for goal in self.goals:
                    if tuple(goal['box'][2:])!=(body['box'][2]+2,body['box'][3]+2):continue
                    if (goal['box'][0]+1,goal['box'][1]+1) in occupied:continue
                    route=self.route(raw,body,goal)
                    if route:choices.append((len(route)+(tuple(body['box'])!=tuple(self.active_box or ())),tuple(body['box']),body,goal,route))
        if choices:
            _,_,body,goal,route=min(choices,key=lambda q:(q[0],q[1],q[3]['box']))
            if tuple(body['box'])!=tuple(self.active_box or ()):
                if 6 not in raw['available_actions']:return dict(done=True,action=None,data={})
                y,x,h,w=body['box'];return self.answer(raw,6,dict(x=x+w//2,y=y+h//2),'test_other_object_selection',body,route,goal)
            return self.answer(raw,route[0],{},'execute_multi_object_route',body,route,goal)
        retry=[a for a in controls if a not in self.motions and self.queries[a]<2]
        if retry:return self.answer(raw,retry[0],{},'retry_unconfirmed_control')
        return dict(done=True,action=None,data={})
