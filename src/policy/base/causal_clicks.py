"""Discover reversible click effects and test simple visible goal hypotheses.

The model is a learned XOR control system over visible pixel values. Effects
must repeat in distinct contexts. Predictions are checked after every planned
intervention, and contradicted effects are discarded. Uniformity is a proposed
goal, never a supplied game rule. Unmodeled pixels are not claimed predicted.
"""
import hashlib
from collections import Counter,defaultdict
import numpy as np
from scipy import ndimage as ndi
from scene_cells import partition,freeze


def bits(a):return int.from_bytes(np.asarray(a,dtype=np.uint8).tobytes(),'little')


def linear_solution(vectors,target):
    basis={};kernel=[]
    for i,vector in enumerate(vectors):
        value=vector;combination=1<<i
        while value:
            pivot=value.bit_length()-1
            if pivot not in basis:basis[pivot]=(value,combination);break
            other,how=basis[pivot];value^=other;combination^=how
        if not value:kernel.append(combination)
    solution=0
    while target:
        pivot=target.bit_length()-1
        if pivot not in basis:return None
        value,how=basis[pivot];target^=value;solution^=how
    # Enumerate a bounded null space to reduce the number of real actions.
    options=[solution]
    for null in kernel[:10]:options.extend([v^null for v in options])
    return min(options,key=lambda v:(v.bit_count(),v))


class CausalClicks:
    def __init__(self):
        self.previous=None;self.observations=defaultdict(list);self.models={};self.first_probe=None
        self.expected=None;self.expected_mask=None;self.predicted_action=None;self.goal_trials=Counter();self.current_goal=None
        self.plans=0;self.probes=0;self.revisions=0;self.verified=0;self.goal_failures=0;self.level=0;self.last=None;self.colors=set()
        self.age=0;self.delegated=0;self.reference_goals=0

    def observe(self,frame,last=None,progress=False,reset=False):
        a=np.asarray(frame,dtype=np.uint8)
        self.age+=1
        if progress or reset:
            self.observations.clear();self.models.clear();self.goal_trials.clear();self.current_goal=None;self.first_probe=None;self.colors.clear()
            self.expected=None;self.expected_mask=None;self.predicted_action=None
            self.age=0;self.delegated=0
        if self.expected is not None and not progress and not reset:
            if np.array_equal(a[self.expected_mask],self.expected[self.expected_mask]):self.verified+=1
            else:
                self.revisions+=1;self.models.pop(self.predicted_action,None);self.observations.pop(self.predicted_action,None);self.current_goal=None
            self.expected=None;self.expected_mask=None;self.predicted_action=None
        if self.previous is not None and last is not None and last[0]==6 and not progress and not reset:
            delta=np.bitwise_xor(self.previous,a);changed=int(np.count_nonzero(delta))
            if changed>=4:
                self.colors.update(map(int,np.unique(self.previous[delta!=0])));self.colors.update(map(int,np.unique(a[delta!=0])))
                state=hashlib.sha256(self.previous.tobytes()).hexdigest()[:16];history=self.observations[last]
                if not any(s==state for s,_ in history):history.append((state,delta.copy()))
                if len(history)>4:del history[0]
                if len(history)==1:self.first_probe=last
                elif len(history)>=2:
                    stack=np.stack([d for _,d in history]);stable=np.all(stack==stack[0],axis=0)
                    effect=np.where(stable,stack[0],0).astype(np.uint8)
                    # Demand spatial support for an inferred variable. Tiny
                    # isolated effects remain outside this partial world model.
                    regions,n=ndi.label(effect!=0)
                    counts=np.bincount(regions.ravel());keep=counts>=4;keep[0]=False;effect[~keep[regions]]=0
                    if np.count_nonzero(effect)>=4:self.models[last]=effect
                    else:self.models.pop(last,None)
        self.previous=None if reset else a.copy();self.last=a
        if self.current_goal is not None and not progress:
            signature,goal_id,mask,desired=self.current_goal
            if np.array_equal(a[mask],desired[mask]):
                self.goal_trials[(signature,goal_id)]+=1;self.goal_failures+=1;self.current_goal=None

    def reference_targets(self,a,mask,effects):
        """Propose an analogous visible, uncontrollable block as a goal."""
        try:sep,rows,cols=partition(freeze(a),'auto')
        except ValueError:return []
        controlled=np.zeros((len(rows),len(cols)),dtype=bool);values=np.zeros_like(controlled,dtype=int);allowed={}
        for i,(y,Y) in enumerate(rows):
            for j,(x,X) in enumerate(cols):
                patch=a[y:Y,x:X];values[i,j]=int(np.bincount(patch.ravel()).argmax())
                controlled[i,j]=float(mask[y:Y,x:X].mean())>=.8
                if controlled[i,j]:
                    yy,xx=np.argwhere(mask[y:Y,x:X])[0]+[y,x]
                    allowed[(i,j)]={int(a[yy,xx])}|{int(a[yy,xx]^e[yy,xx]) for e in effects}
        cells=np.argwhere(controlled)
        if len(cells)<4:return []
        lo=cells.min(0);hi=cells.max(0)+1;rh,cw=hi-lo
        if min(rh,cw)<2 or not controlled[lo[0]:hi[0],lo[1]:hi[1]].all():return []
        targets=[]
        for r in range(len(rows)-rh+1):
            for c in range(len(cols)-cw+1):
                if controlled[r:r+rh,c:c+cw].any():continue
                goal=values[r:r+rh,c:c+cw]
                if len(np.unique(goal))<2:continue
                if any(int(goal[i,j]) not in allowed[(int(lo[0]+i),int(lo[1]+j))] for i in range(rh) for j in range(cw)):continue
                desired=a.copy()
                for i in range(rh):
                    for j in range(cw):
                        y,Y=rows[lo[0]+i];x,X=cols[lo[1]+j];piece=desired[y:Y,x:X];piece[mask[y:Y,x:X]]=goal[i,j]
                targets.append(('reference_%s_%s'%(r,c),desired))
        return targets

    def choose(self,legal):
        if 6 not in legal or self.last is None:return None
        # Preserve the initial exploration policy, and bound how long an
        # unconfirmed model can take control without actual level progress.
        if self.age<40 or self.delegated>=64:return None
        if self.first_probe is not None:
            key=self.first_probe;self.first_probe=None
            # An immediate repeated intervention distinguishes reversible
            # effects from one-way destruction or an incidental animation.
            if len(self.observations[key])==1:self.probes+=1;self.delegated+=1;return key
        if len(self.models)<2:return None
        a=self.last;unique={}
        for action,effect in sorted(self.models.items()):unique.setdefault(bits(effect),(action,effect))
        entries=list(unique.values());effects=[v[1] for v in entries];vectors=list(unique)
        mask=np.any(np.stack(effects)!=0,axis=0)
        if np.count_nonzero(mask)<8:return None
        signature=hashlib.sha256(b''.join(v.tobytes() for v in effects)).hexdigest()[:16]
        # Uniform observed colors are hypotheses about a latent objective.
        # Failure to finish falsifies that goal for the current learned system.
        colors=sorted(set(map(int,np.unique(a[mask])))|self.colors)
        goals=self.reference_targets(a,mask,effects)
        self.reference_goals+=len(goals)
        for color in colors:
            goals.append(('uniform_'+str(color),np.where(mask,color,a).astype(np.uint8)))
        solutions=[]
        for goal_id,desired in goals:
            if self.goal_trials[(signature,goal_id)]>=1:continue
            target=bits(np.bitwise_xor(a,desired))
            if target==0:continue
            solution=linear_solution(vectors,target)
            if solution is not None and solution:
                solutions.append((0 if goal_id.startswith('reference') else 1,solution.bit_count(),goal_id,solution,desired))
        if not solutions:return None
        _,_,goal_id,solution,desired=min(solutions,key=lambda s:s[:4])
        index=(solution&-solution).bit_length()-1;action,effect=entries[index]
        self.expected=np.bitwise_xor(a,effect);self.expected_mask=mask.copy();self.predicted_action=action
        self.current_goal=(signature,goal_id,mask.copy(),desired.copy());self.plans+=1;self.delegated+=1
        return action

    def diagnostics(self):
        return {'click_effect_models':len(self.models),'causal_click_probes':self.probes,'causal_click_plans':self.plans,'causal_predictions_verified':self.verified,'causal_model_revisions':self.revisions,'visible_goal_hypotheses_falsified':self.goal_failures,'visible_reference_hypotheses':self.reference_goals,'delegated_this_level':self.delegated}
