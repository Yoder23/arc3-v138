"""Intermediate landmarks and observed-context input experiments after a stalled goal."""
from collections import Counter,deque
import copy
from matrix_motion_learner_v6 import Agent as Base,objects
from observed_edit_completion_v1 import EditLoop

def inside(y,x,box):
    a,b,h,w=box;return a<=y<a+h and b<=x<b+w

def reachable(agent,raw):
    b=agent.moving
    if not b:return {},None
    start=tuple(b['box'][:2]);h,w=b['box'][2:];bg=Counter(v for row in raw['frame'] for v in row).most_common(1)[0][0]
    parents={start:None};todo=deque([start])
    while todo and len(parents)<4096:
        p=todo.popleft()
        for action,m in sorted(agent.motions.items()):
            q=(p[0]+m['delta'][0],p[1]+m['delta'][1])
            if q in parents or (p,action,agent.program_index) in agent.blocked:continue
            if not(0<=q[0]<=64-h and 0<=q[1]<=64-w):continue
            if any(inside(y,x,agent.grid['box']) or raw['frame'][y][x]==bg for y in range(q[0],q[0]+h) for x in range(q[1],q[1]+w)):continue
            parents[q]=(p,action);todo.append(q)
    return parents,bg

def path(parents,p):
    out=[]
    while parents[p] is not None:p,a=parents[p];out.append(a)
    return out[::-1]

def gap(a,b):
    y,x,h,w=a;v,u,hh,ww=b
    return max(v-(y+h),y-(v+hh),0)+max(u-(x+w),x-(u+ww),0)

class Agent(Base):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.exploring=False;self.experiment=None;self.experiment_log=[];self.attempted=set();self.selection_record=None;self.extra_actions=0;self.context_revisions=[];self.navigation_only=False
    def observe(self,raw):
        old=self.previous
        super().observe(raw)
        if not old or old['raw']['state']!=raw['state'] or old['raw']['levels_completed']!=raw['levels_completed'] or self.grid is None:return
        if old['action']==6 and self.moving and self.moving.get('parts'):
            candidates=[o for o in objects(raw['frame'],[self.grid['box']]) if o.get('parts') and o['ink']==self.moving['ink']]
            if len(candidates)==1:
                size_changed=candidates[0]['box'][2:]!=self.moving['box'][2:]
                self.moving=candidates[0]
                if size_changed:self.motions={};self.blocked=set();self.trials=Counter()
            else:self.moving=None
        if old['action']==6 and self.selection_record is None:
            x,y=old['data']['x'],old['data']['y'];a=old['raw']['frame'][y][x];b=raw['frame'][y][x]
            other=[(v,u) for v,u,h,w in self.grid['cells'] if not inside(y,x,(v,u,h,w))]
            if inside(y,x,self.grid['box']) and a!=b and all(old['raw']['frame'][v][u]==raw['frame'][v][u] for v,u in other):
                self.selection_record=dict(source=old['source'],point=(x,y),before=a,ink=b)
        if self.exploring and self.experiment and old['certificate'].get('intermediate_plan',{}).get('phase')=='clear_input':
            x,y=old['data']['x'],old['data']['y']
            if old['raw']['frame'][y][x]==raw['frame'][y][x]:self.experiment['clear_no_effects'][x,y]+=1
        if self.exploring:
            exclusions=[self.grid['box']]
            if old['certificate'].get('moving'):exclusions.append(old['certificate']['moving']['box'])
            if self.moving:exclusions.append(self.moving['box'])
            changed={(y,x) for y in range(64) for x in range(64) if old['raw']['frame'][y][x]!=raw['frame'][y][x] and not any(inside(y,x,box) for box in exclusions)}
            removed=[]
            for p,a,program in list(self.blocked):
                if a not in self.motions or not self.moving:continue
                dy,dx=self.motions[a]['delta'];h,w=self.moving['box'][2:];q=p[0]+dy,p[1]+dx
                if any(inside(y,x,(q[0],q[1],h,w)) for y,x in changed):
                    self.blocked.remove((p,a,program));removed.append((p,a,program))
            if removed:self.context_revisions.append(dict(source=old['source'],changed=sorted(changed),invalidated=removed))
    def issue(self,raw,action,data,phase,route=None,extra=None):
        p=dict(phase=phase,landmark=copy.deepcopy(self.experiment['landmark']) if self.experiment else None,route=route or [],selection=copy.deepcopy(self.selection_record),revisions=copy.deepcopy(self.context_revisions),hypothesis='test_visible_intermediate_object_before_retrying_the_goal')
        self.extra_actions+=1
        return self.answer(raw,action,data,'intermediate_'+phase,dict(intermediate_plan=p,**(extra or {})))
    def respond(self,raw):
        boundary=raw['levels_completed']!=self.level or raw['state']!='NOT_FINISHED'
        if boundary:
            self.exploring=False;self.experiment=None;self.attempted=set();self.selection_record=None;self.extra_actions=0;self.context_revisions=[]
        if not self.exploring:
            response=super().respond(raw)
            if not response['done'] or raw['state']!='NOT_FINISHED' or not self.moving or not self.motions:return response
            self.exploring=True
        else:
            self.observe(raw)
        if self.contact and self.extra_actions<160:
            if self.contact['attempt']<self.contact['limit']:
                self.contact['attempt']+=1;self.extra_actions+=1
                return self.answer(raw,self.contact['action'],{},'test_goal_contact',dict(goal_contact=copy.deepcopy(self.contact)))
            self.contact=None
        if self.extra_actions>=160 or not self.moving:return dict(done=True,action=None,data={})
        unknown=[a for a in raw['available_actions'] if a not in (0,6,7) and a not in self.motions and self.trials[a]<2]
        if unknown:return self.issue(raw,min(unknown,key=lambda a:(self.trials[a],a)),{},'motion_inquiry')
        parents,bg=reachable(self,raw);at=tuple(self.moving['box'][:2]);h,w=self.moving['box'][2:]
        goals=[q for q in parents if any(inside(q[0],q[1],g['box']) for g in self.goals)]
        if goals:
            p=min(goals,key=lambda q:(len(path(parents,q)),q));route=path(parents,p)
            if route:return self.issue(raw,route[0],{},'goal_route',route)
        if self.experiment is None:
            choices=[]
            palette=set(self.moving['ink']) if isinstance(self.moving['ink'],(tuple,list)) else {self.moving['ink']}
            for landmark in objects(raw['frame'],[self.grid['box']]):
                if landmark.get('parts') or landmark['ink'] in palette|{bg} or landmark['ink'] in self.passable:continue
                key=tuple(landmark['box']),landmark['ink']
                if key in self.attempted:continue
                poses=[q for q in parents if gap(q+(h,w),landmark['box'])<=1]
                if not poses:continue
                pose=min(poses,key=lambda q:(gap(q+(h,w),landmark['box']),abs(2*q[0]+h-2*landmark['box'][0]-landmark['box'][2])+abs(2*q[1]+w-2*landmark['box'][1]-landmark['box'][3]),len(path(parents,q)),q))
                choices.append((len(path(parents,pose)),landmark['box'],key,pose,landmark))
            if not choices:return dict(done=True,action=None,data={})
            _,_,key,pose,landmark=min(choices,key=lambda p:p[:2]);self.attempted.add(key)
            self.experiment=dict(landmark=dict(landmark,observed_at=self.t),pose=pose,phase='approach',start=self.t,clear_steps=0,clear_no_effects=Counter(),edit=None,edit_start=None)
        exp=self.experiment
        if exp['phase']=='approach':
            if exp['pose'] not in parents:
                self.experiment_log.append(dict(start=exp['start'],end=self.t,outcome='approach_refuted',landmark=exp['landmark']));self.experiment=None
                return self.respond_after_refutation(raw)
            route=path(parents,exp['pose'])
            if route:return self.issue(raw,route[0],{},'approach',route)
            if self.navigation_only:
                self.experiment=None;return self.respond_after_refutation(raw)
            exp['phase']='clear'
            y,x,hh,ww=exp['landmark']['box']
            return self.issue(raw,6,dict(x=x+(ww-1)//2,y=y+(hh-1)//2),'contact')
        if exp['phase']=='clear':
            selected=[]
            if self.selection_record:
                ink=self.selection_record['ink']
                for y,x,hh,ww in self.grid['cells']:
                    if raw['frame'][y][x]==ink and exp['clear_no_effects'][x+(ww-1)//2,y+(hh-1)//2]<2:selected.append((x+(ww-1)//2,y+(hh-1)//2))
            if selected and exp['clear_steps']<2*len(self.grid['cells']):
                exp['clear_steps']+=1;x,y=selected[0]
                return self.issue(raw,6,dict(x=x,y=y),'clear_input')
            exp['phase']='program';exp['edit']=EditLoop(self.programs[0]);exp['edit_start']=self.t
        if exp['phase']=='program':
            proposal=exp['edit'].propose(raw)
            if proposal:
                return self.issue(raw,proposal['action'],proposal['data'],'reapply_program',extra=dict(edit=proposal['certificate'],edit_start=exp['edit_start']))
            self.experiment_log.append(dict(start=exp['start'],end=self.t,landmark=exp['landmark'],outcome='input_completed' if exp['edit'].completed(raw) else 'input_unconfirmed',input_effect_is_hypothesis=True))
            self.experiment=None
            return self.respond_after_refutation(raw)
        return dict(done=True,action=None,data={})
    def respond_after_refutation(self,raw):
        # No second observation of the same transition. Choose the next
        # intermediate object on the next call by a bounded neutral probe.
        available=[a for a in raw['available_actions'] if a in self.motions]
        if not available:return dict(done=True,action=None,data={})
        a=min(available,key=lambda a:(self.trials[a],a))
        return self.issue(raw,a,{},'alternative_probe')

