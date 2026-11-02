"""Infer categorical interventions from visible repeated rectangular cells.

The representation and factorization are hypotheses. Contradictory transitions
invalidate a model; actual public outcomes alone establish goal attainment.
No environment identifier, supplied action meaning, target state or game source
is accepted. This is a limited reusable visual/control grammar, not a brain.
"""
from collections import Counter,defaultdict
from itertools import product
import numpy as np
from scipy import ndimage


def cells(frame):
    a=np.asarray(frame);bg=int(np.bincount(a.ravel()).argmax());groups=defaultdict(list)
    for color in np.unique(a):
        if color==bg:continue
        labels,_=ndimage.label(a==color)
        for i,sl in enumerate(ndimage.find_objects(labels),1):
            if sl is None:continue
            mask=labels[sl]==i;h,w=mask.shape
            if 2<=min(h,w) and max(h,w)<=24 and mask.all():
                groups[(h,w)].append((sl[0].start,sl[1].start,h,w))
    candidates=[sorted(v) for v in groups.values() if 4<=len(v)<=64]
    return max(candidates,key=lambda v:(len(v),v[0][2]*v[0][3],v),default=[])


def values(frame,slots):
    a=np.asarray(frame);result=[]
    for y,x,h,w in slots:
        patch=a[y:y+h,x:x+w]
        if patch.shape!=(h,w) or not np.all(patch==patch[0,0]):return None
        result.append(int(patch[0,0]))
    return tuple(result)


def field_solution(matrix,target,prime,limit=256):
    """Solve an inferred modular action system; minimize a bounded null space."""
    a=np.asarray(matrix,dtype=np.int64)%prime;b=np.asarray(target,dtype=np.int64)%prime
    if a.ndim!=2:return None
    n,m=a.shape;aug=np.concatenate((a,b[:,None]),axis=1);pivots=[];row=0
    for col in range(m):
        found=next((i for i in range(row,n) if aug[i,col]),None)
        if found is None:continue
        aug[[row,found]]=aug[[found,row]]
        aug[row]=(aug[row]*pow(int(aug[row,col]),prime-2,prime))%prime
        for i in range(n):
            if i!=row and aug[i,col]:aug[i]=(aug[i]-aug[i,col]*aug[row])%prime
        pivots.append(col);row+=1
        if row==n:break
    if any(not aug[i,:m].any() and aug[i,m] for i in range(row,n)):return None
    base=np.zeros(m,dtype=np.int64)
    for i,col in enumerate(pivots):base[col]=aug[i,m]
    free=[j for j in range(m) if j not in pivots];kernel=[]
    for j in free:
        v=np.zeros(m,dtype=np.int64);v[j]=1
        for i,col in enumerate(pivots):v[col]=-aug[i,j]%prime
        kernel.append(v)
    best=base;best_key=(int(base.sum()),tuple(base))
    for i,coefs in enumerate(product(range(prime),repeat=min(len(kernel),8))):
        if i>=limit:break
        candidate=(base+sum((c*v for c,v in zip(coefs,kernel)),np.zeros(m,dtype=np.int64)))%prime
        key=(int(candidate.sum()),tuple(candidate))
        if key<best_key:best,best_key=candidate,key
    return best.tolist()


class Effect:
    def __init__(self,n):
        self.edges=[{} for _ in range(n)];self.changed=set();self.count=0;self.conflict=False

    def learn(self,before,after):
        self.count+=1
        for i,(a,b) in enumerate(zip(before,after)):
            if a in self.edges[i] and self.edges[i][a]!=b:self.conflict=True
            self.edges[i][a]=b
            if a!=b:self.changed.add(i)

    def predict(self,state):
        if self.conflict or self.count<2:return None
        result=list(state)
        for i in self.changed:
            if state[i] not in self.edges[i]:return None
            result[i]=self.edges[i][state[i]]
        return tuple(result)


class CategoricalClicks:
    def __init__(self):
        self.slots=[];self.previous=None;self.last=None;self.models={};self.finished=set()
        self.probe=None;self.expected=None;self.expected_action=None;self.current_goal=None
        self.rejected_goals=set();self.probes=0;self.plans=0;self.verified=0;self.revisions=0
        self.goal_failures=0;self.unsupported=0;self.delegated=0;self.age=0

    def clear(self):
        self.slots=[];self.previous=None;self.last=None;self.models={};self.finished=set()
        self.probe=None;self.expected=None;self.expected_action=None;self.current_goal=None
        self.rejected_goals=set();self.delegated=0;self.age=0

    def observe(self,frame,last=None,progress=False,reset=False):
        if progress or reset:self.clear()
        self.age+=1
        if not self.slots:self.slots=cells(frame)
        state=values(frame,self.slots) if self.slots else None
        if state is None:
            self.unsupported+=1;self.previous=None;self.last=None;self.probe=None
            self.expected=None;return
        if self.expected is not None:
            if state==self.expected:self.verified+=1
            else:
                self.revisions+=1
                if self.expected_action in self.models:self.models[self.expected_action].conflict=True
                self.finished.discard(self.expected_action)
            self.expected=None
        if self.previous is not None and last in self.actions():
            effect=self.models.setdefault(last,Effect(len(state)))
            effect.learn(self.previous,state)
            if effect.conflict:self.revisions+=1
        if self.probe is not None and last==self.probe['action']:
            self.probe['steps']+=1
            repeated=state in self.probe['seen']
            self.probe['seen'].add(state)
            if (repeated and self.probe['steps']>=2) or self.probe['steps']>=16:
                self.finished.add(last);self.probe=None
        if self.current_goal is not None and state==self.current_goal[1]:
            self.rejected_goals.add(self.current_goal[0]);self.goal_failures+=1;self.current_goal=None
        self.previous=state;self.last=state

    def actions(self):
        return [(6,x+(w-1)//2,y+(h-1)//2) for y,x,h,w in self.slots]

    def goals(self,state,controlled):
        slots=self.slots;position={(y,x):i for i,(y,x,_,_) in enumerate(slots)}
        goals=[];used=set(controlled)
        if len(used)>=4:
            first=min(used);y,x,_,_=slots[first]
            for j,(yy,xx,_,_) in enumerate(slots):
                if j in used:continue
                dy,dx=yy-y,xx-x;mapping={}
                for i in used:
                    sy,sx,_,_=slots[i];other=position.get((sy+dy,sx+dx))
                    if other is None or other in used:break
                    mapping[i]=other
                if len(mapping)!=len(used):continue
                desired=list(state)
                for i,j in mapping.items():desired[i]=state[j]
                if len({desired[i] for i in used})>=2:
                    goals.append((('reference',tuple(sorted(used)),dy,dx),tuple(desired),0))
        for color in sorted(set(state)):
            desired=tuple(color if i in used else value for i,value in enumerate(state))
            goals.append((('uniform',tuple(sorted(used)),color),desired,1))
        result=[]
        for key,desired,priority in goals:
            if desired==state:self.rejected_goals.add(key)
            if key not in self.rejected_goals:result.append((key,desired,priority))
        return result

    def modular_plan(self,state,desired,entries,controlled):
        orders={};prime=None
        for i in controlled:
            for _,effect in entries:
                mapping=effect.edges[i]
                if i not in effect.changed or len(mapping) not in (2,3,5,7,11,13):continue
                if set(mapping)!=set(mapping.values()):continue
                cycle=[min(mapping)]
                while mapping[cycle[-1]] not in cycle:cycle.append(mapping[cycle[-1]])
                if mapping[cycle[-1]]!=cycle[0] or len(cycle)!=len(mapping):continue
                if state[i] not in cycle or desired[i] not in cycle:continue
                orders[i]=cycle;break
            if i not in orders:return None
            if prime is None:prime=len(orders[i])
            if len(orders[i])!=prime:return None
        vectors=[];actions=[]
        for action,effect in entries:
            vector=[];valid=True
            for i in controlled:
                cycle=orders[i]
                if i not in effect.changed:vector.append(0);continue
                mapping=effect.edges[i]
                if any(v not in mapping or mapping[v] not in cycle for v in cycle):valid=False;break
                shifts={(cycle.index(mapping[v])-j)%prime for j,v in enumerate(cycle)}
                if len(shifts)!=1:valid=False;break
                vector.append(next(iter(shifts)))
            if valid:actions.append(action);vectors.append(vector)
        if not actions:return None
        target=[(orders[i].index(desired[i])-orders[i].index(state[i]))%prime for i in controlled]
        solution=field_solution(np.asarray(vectors).T,target,prime)
        if solution is None:return None
        plan=[action for action,count in zip(actions,solution) for _ in range(count)]
        # Even an algebraic plan must replay the actual learned categorical maps.
        simulated=state;effects=dict(entries)
        for action in plan:
            simulated=effects[action].predict(simulated)
            if simulated is None:return None
        return plan if simulated==desired else None

    def choose(self,legal):
        if 6 not in legal or self.last is None or len(self.slots)<4 or self.delegated>=160:return None
        actions=self.actions();state=self.last
        if self.probe is not None:
            self.probes+=1;self.delegated+=1;return self.probe['action']
        untried=[a for a in actions if a not in self.finished]
        if untried:
            action=untried[0]
            # Contradicted factorization is unsupported; don't repeat forever.
            if action in self.models and self.models[action].conflict:
                self.finished.add(action);return None
            self.probe={'action':action,'seen':{state},'steps':0}
            self.probes+=1;self.delegated+=1;return action
        entries=[(a,e) for a,e in sorted(self.models.items()) if e.count>=2 and not e.conflict and e.changed]
        controlled=sorted(set().union(*(e.changed for _,e in entries))) if entries else []
        if not controlled:return None
        candidates=[]
        for key,desired,priority in self.goals(state,controlled):
            plan=self.modular_plan(state,desired,entries,controlled)
            if plan:candidates.append((priority,len(plan),str(key),key,desired,plan))
            else:
                # A learned irreversible setter need not form a group. Take a
                # verified one-step reduction of a visible goal discrepancy.
                before=sum(a!=b for a,b in zip(state,desired))
                for action,effect in entries:
                    predicted=effect.predict(state)
                    if predicted is None:continue
                    after=sum(a!=b for a,b in zip(predicted,desired))
                    if after<before:candidates.append((priority,after+1,str(key),key,desired,[action]))
        if not candidates:return None
        _,_,_,key,desired,plan=min(candidates,key=lambda row:row[:3])
        action=plan[0];self.expected=self.models[action].predict(state);self.expected_action=action
        self.current_goal=(key,desired);self.plans+=1;self.delegated+=1
        return action

    def diagnostics(self):
        return {'categorical_cells':len(self.slots),'categorical_models':sum(e.count>=2 and not e.conflict for e in self.models.values()),
                'categorical_probes':self.probes,'categorical_plans':self.plans,
                'categorical_predictions_verified':self.verified,'categorical_revisions':self.revisions,
                'categorical_goal_failures':self.goal_failures,'categorical_unsupported_frames':self.unsupported}
