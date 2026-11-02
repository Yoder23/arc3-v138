"""Symbolic intervention version spaces, not a neural/biological model.

Affected outputs must agree across all surviving cross-cell copy and local
color-map hypotheses. The optional generalized mode extrapolates a unique copy
relation after three observed source values when the own-cell color is unseen.
Otherwise unknown local colors cause abstention. Unchanged outputs
provisionally use identity. Every executed prediction is checked next frame.
"""
from collections import Counter, defaultdict, deque
import hashlib
import numpy as np
from scipy import ndimage
from categorical import cells as filled_cells, values as filled_values, CategoricalClicks

def shape_mask(h,w,kind):
    y,x=np.indices((h,w))
    if kind=='solid':return np.ones((h,w),dtype=bool)
    if kind=='outline':return (y==0)|(y==h-1)|(x==0)|(x==w-1)
    return (y==h//2)|(x==w//2)

def shape_cells(frame):
    a=np.asarray(frame);bg=int(np.bincount(a.ravel()).argmax());groups=defaultdict(list)
    for color in np.unique(a):
        if color==bg:continue
        labels,_=ndimage.label(a==color)
        for i,sl in enumerate(ndimage.find_objects(labels),1):
            if sl is None:continue
            mask=labels[sl]==i;h,w=mask.shape
            if not (3<=min(h,w) and max(h,w)<=24):continue
            if any(np.array_equal(mask,shape_mask(h,w,k)) for k in ('solid','outline','cross')):
                groups[(h,w)].append((sl[0].start,sl[1].start,h,w))
    groups=[sorted(v) for v in groups.values() if 4<=len(v)<=64]
    return max(groups,key=lambda v:(len(v),v[0][2]*v[0][3],v),default=[])

def shape_values(frame,slots):
    a=np.asarray(frame);bg=int(np.bincount(a.ravel()).argmax());result=[]
    for y,x,h,w in slots:
        p=a[y:y+h,x:x+w]
        if p.shape!=(h,w):return None
        colors=set(map(int,p.ravel()))-{bg}
        if len(colors)!=1:return None
        color=next(iter(colors));mask=p==color
        if not any(np.array_equal(mask,shape_mask(h,w,k)) for k in ('solid','outline','cross')):return None
        result.append(color)
    return tuple(result)


def extended_values(frame,slots):
    a=np.asarray(frame);bg=int(np.bincount(a.ravel()).argmax());result=[]
    for y,x,h,w in slots:
        if y<0 or x<0 or y+h>a.shape[0] or x+w>a.shape[1]:return None
        patch=a[y:y+h,x:x+w]
        if np.all(patch==patch[0,0]):
            result.append(int(patch[0,0]));continue
        colors=set(map(int,patch.ravel()))-{bg}
        if len(colors)==1:
            color=next(iter(colors));mask=patch==color
            if any(np.array_equal(mask,shape_mask(h,w,k)) for k in ('solid','outline','cross')):
                result.append(color);continue
        payload=bytes([h,w])+np.asarray(patch,dtype=np.uint8).tobytes(order='C')
        result.append(16+int.from_bytes(hashlib.sha256(payload).digest(),'big'))
    return tuple(result)

class DependencyEffect:
    def __init__(self,n,cross=True,generalize=False):
        self.n=n;self.cross=cross;self.generalize=generalize;self.history=[];self.changed=set();self.copies=[set(range(n)) for _ in range(n)]
        self.maps=[{} for _ in range(n)];self.local_valid=[True]*n;self.count=0
    def learn(self,before,after):
        self.count+=1
        if (before,after) not in self.history:
            self.history.append((before,after))
            if len(self.history)>32:self.history.pop(0)
        # Bounded history allows eventual relearning after changed dynamics.
        self.changed=set();self.copies=[set(range(self.n)) for _ in range(self.n)]
        self.maps=[{} for _ in range(self.n)];self.local_valid=[True]*self.n
        for old,new in self.history:
            for i,(a,b) in enumerate(zip(old,new)):
                if a!=b:self.changed.add(i)
                self.copies[i].intersection_update(k for k in range(self.n) if old[k]==b)
                if a in self.maps[i] and self.maps[i][a]!=b:self.local_valid[i]=False
                self.maps[i][a]=b
    def predict(self,state):
        if len({old for old,new in self.history})<2:return None
        out=list(state)
        for i in self.changed:
            candidates={state[k] for k in self.copies[i]} if self.cross else set()
            if self.local_valid[i]:
                if state[i] not in self.maps[i]:
                    sources=self.copies[i] if self.cross else set()
                    if not self.generalize or len(sources)!=1:return None
                    source=next(iter(sources))
                    if len({old[source] for old,new in self.history})<3:return None
                else:candidates.add(self.maps[i][state[i]])
            if len(candidates)!=1:return None
            out[i]=next(iter(candidates))
        return tuple(out)

class DependencyClicks:
    def __init__(self,shapes=False,cross=True,generalize=False):
        self.shapes=shapes;self.cross=cross;self.generalize=generalize;self.probes=0;self.plans=0;self.verified=0;self.revisions=0
        self.unsupported=0;self.goal_failures=0;self.expansions=0;self.spatial_aliases=False;self.spatial_alias_observations=0;self.extrapolated_actions=0;self.extended_states=False;self.extended_supported_frames=0;self.model_experiments=False;self.model_experiment_steps=0;self.model_experiment_expansions=0;self.clear()
    def clear(self):
        self.slots=[];self.previous=None;self.last=None;self.models={};self.expected=None
        self.current_goal=None;self.rejected_goals=set();self.delegated=0;self.pending=[]
        self.certificate=None;self.action_visits=Counter();self.state_visits=Counter()
    def values(self,frame):
        if self.extended_states:return extended_values(frame,self.slots)
        return (shape_values if self.shapes else filled_values)(frame,self.slots)
    def actions(self):return [(6,x+(w-1)//2,y+(h-1)//2) for y,x,h,w in self.slots]
    def observe(self,frame,last=None,progress=False,reset=False):
        if progress or reset:self.clear()
        if not self.slots:self.slots=(shape_cells if self.shapes else filled_cells)(frame)
        state=self.values(frame) if self.slots else None
        if self.extended_states and state is not None and (shape_values if self.shapes else filled_values)(frame,self.slots) is None:self.extended_supported_frames+=1
        if state is None:
            self.unsupported+=1;self.previous=None;self.last=None;self.expected=None
            self.certificate=None;self.pending=[];return
        if self.expected is not None:
            if state==self.expected:self.verified+=1
            else:self.revisions+=1;self.pending=[]
            self.expected=None
        # A visible cell's rectangular footprint proposes action equivalence.
        # The existing version space must explain every observed transition.
        # Conflicting outcomes remove its predictive authority; this is not a
        # claim that all coordinates inside every visible object are equivalent.
        if self.spatial_aliases and self.previous is not None and last is not None and last[0]==6:
            aliases=[action for (y,x,h,w),action in zip(self.slots,self.actions())
                     if x<=last[1]<x+w and y<=last[2]<y+h]
            if len(aliases)==1 and aliases[0]!=last:
                last=aliases[0];self.spatial_alias_observations+=1
        if self.previous is not None and last in self.actions():
            self.models.setdefault(last,DependencyEffect(len(state),self.cross,self.generalize)).learn(self.previous,state)
        if self.current_goal is not None and state==self.current_goal[1]:
            self.rejected_goals.add(self.current_goal[0]);self.goal_failures+=1;self.current_goal=None;self.pending=[]
        self.previous=state;self.last=state;self.state_visits[state]+=1;self.certificate=None
    def goals(self,state,controlled):
        # Authored reference/uniform grammar, not a learned general goal model.
        return CategoricalClicks.goals(self,state,controlled)
    def plan(self,state,entries,goals):
        if not goals:return None
        desired={v:(k,p) for k,v,p in goals};q=deque([state]);paths={state:[]}
        while q and len(paths)<=2048:
            old=q.popleft();self.expansions+=1
            if len(paths[old])>=12:continue
            for action,effect in entries:
                new=effect.predict(old)
                if new is None or new in paths:continue
                path=paths[old]+[(action,new)]
                if new in desired:
                    key,priority=desired[new];return key,new,path
                if len(paths)>=2048:continue
                paths[new]=path;q.append(new)
        return None
    def experiment_plan(self,state,entries):
        # A model forecast is a tentative experiment, never evidence of success.
        # Only actions whose version spaces agree may be simulated.
        paths={state:[]};queue=deque([state])
        while queue and len(paths)<512:
            old=queue.popleft();self.model_experiment_expansions+=1
            if len(paths[old])>=6:continue
            for action,effect in entries:
                new=effect.predict(old)
                if new is None or new in paths:continue
                path=paths[old]+[(action,new)];paths[new]=path
                if not self.state_visits[new]:return path
                if len(paths)>=512:break
                queue.append(new)
        return None
    def choose(self,legal):
        if 6 not in legal or self.last is None or len(self.slots)<4 or self.delegated>=224:return None
        state=self.last;actions=self.actions()
        entries=[(a,e) for a,e in sorted(self.models.items()) if e.changed]
        controlled=sorted(set().union(*(e.changed for a,e in entries))) if entries else []
        goals=self.goals(state,controlled) if controlled else [];plan=None
        if self.pending and self.current_goal in [(k,g) for k,g,p in goals]:
            simulated=state;valid=True
            for action,expected in self.pending:
                simulated=self.models[action].predict(simulated)
                if simulated!=expected:valid=False;break
            if valid and simulated==self.current_goal[1]:
                plan=(*self.current_goal,self.pending)
        if plan is None and controlled and self.delegated%2==0:
            plan=self.plan(state,entries,sorted(goals,key=lambda t:(t[2],str(t[0]))))
        experiment=self.experiment_plan(state,entries) if plan is None and self.model_experiments and entries else None
        if plan is not None:
            key,desired,path=plan;action,predicted=path[0];self.pending=path[1:]
            effect=self.models[action]
            self.extrapolated_actions+=int(any(effect.local_valid[i] and state[i] not in effect.maps[i] for i in effect.changed))
            self.expected=predicted;self.current_goal=(key,desired);self.plans+=1
            self.certificate={'kind':'plan','before':state,'slots':self.slots,'goal_key':key,'goal':desired,'path':path}
        elif experiment:
            action,predicted=experiment[0];self.expected=predicted
            self.pending=[];self.current_goal=None;self.model_experiment_steps+=1
            self.certificate={'kind':'experiment','before':state,'slots':self.slots,'path':experiment,'unvisited_target':experiment[-1][1]}
        else:
            self.pending=[];candidates=[]
            for action in actions:
                effect=self.models.get(action);contexts={old for old,new in effect.history} if effect else set()
                inert=bool(effect and not effect.changed and len(contexts)>=2)
                digest=hashlib.sha256(repr((state,action)).encode()).hexdigest()
                candidates.append(((inert,state in contexts,len(contexts),self.action_visits[action],digest),action))
            action=min(candidates)[1];self.probes+=1
            self.certificate={'kind':'probe','before':state,'slots':self.slots,'action':action}
        self.action_visits[action]+=1;self.delegated+=1;return action
    def diagnostics(self):
        cross=sum(self.cross and any(k!=i for k in e.copies[i]) and not e.local_valid[i] for e in self.models.values() for i in e.changed)
        return {'model_experiment_steps':self.model_experiment_steps,'model_experiment_expansions':self.model_experiment_expansions,'extended_state_supported_frames':self.extended_supported_frames,'dependency_extrapolated_actions':self.extrapolated_actions,'spatial_alias_observations':self.spatial_alias_observations,'dependency_cells':len(self.slots),'dependency_models':len(self.models),'dependency_cross_outputs':cross,
                'dependency_probes':self.probes,'dependency_plans':self.plans,'dependency_predictions_verified':self.verified,
                'dependency_revisions':self.revisions,'dependency_goal_failures':self.goal_failures,
                'dependency_unsupported_frames':self.unsupported,'dependency_expansions':self.expansions}
