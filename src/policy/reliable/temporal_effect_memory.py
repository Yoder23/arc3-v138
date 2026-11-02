"""Episode-local recent-action effect hypotheses from unique visible appearances.

This is a prediction probe, not actor/causal attribution or a goal planner.
"""
from collections import defaultdict
from evidence import components,primitive_components,observation,digest

def visible(obs):
    groups=defaultdict(list)
    for part in components(obs['frame']):
        signature=(part['label'],tuple(tuple(p) for p in part['shape_rc']))
        groups[signature].append(part)
    return {k:v[0] for k,v in groups.items() if len(v)==1}

def primitive_visible(obs):
    groups=defaultdict(list)
    for part in primitive_components(obs['frame']):
        signature=(part['label'],tuple(tuple(p) for p in part['shape_rc']))
        groups[signature].append(part)
    return {k:v[0] for k,v in groups.items() if len(v)==1}

class Memory:
    def __init__(self,contextual):
        self.parts=visible;self.contextual=contextual;self.rows=defaultdict(list);self.moved=set();self.previous=None;self.earlier=None;self.seen=set()
    def predict(self,before,action):
        out=[]
        for signature,part in self.parts(before).items():
            if signature not in self.moved:continue
            allrows=self.rows[(signature,action)];moving=[r for r in allrows if r['delta']!=(0,0)]
            outcomes={r['delta'] for r in moving};rows=allrows;status='global'
            if len(outcomes)>1 and self.contextual:
                rows=[r for r in allrows if r['previous']==self.previous];moving=[r for r in rows if r['delta']!=(0,0)]
                outcomes={r['delta'] for r in moving};status='previous_action_context'
                if len({r['earlier'] for r in moving})<2:continue
            if len(outcomes)!=1 or len(moving)<2 or len({r['origin'] for r in moving})<2:continue
            delta=next(iter(outcomes));origin=tuple(part['origin_rc'])
            if any(r['origin']==origin and r['delta']!=delta for r in rows):continue
            out.append(dict(label=signature[0],shape_rc=[list(p) for p in signature[1]],origin_rc=list(origin),delta_rc=list(delta),status=status,
                previous_action=self.previous,support=[r['evidence_hash'] for r in moving],
                assumptions=['stable unique appearance correspondence','unblocked effect at unobserved position','recent action context sufficient; not a causal claim']))
        return out
    def observe(self,before,action,after):
        before=observation(before);after=observation(after);h=digest(dict(before=before,action=action,after=after,previous=self.previous,earlier=self.earlier))
        # Distinct events with identical observations are allowed; the caller's
        # prospective chain establishes event identity. No fabricated support.
        left,right=self.parts(before),self.parts(after);measured={}
        boundary=after['state']!='NOT_FINISHED' or before['levels_completed']!=after['levels_completed']
        same_shape=(len(before['frame']),len(before['frame'][0]))==(len(after['frame']),len(after['frame'][0]))
        if not boundary and same_shape:
            for key,part in left.items():
                if key not in right:continue
                origin=tuple(part['origin_rc']);delta=tuple(right[key]['origin_rc'][i]-origin[i] for i in (0,1))
                row=dict(origin=origin,delta=delta,previous=self.previous,earlier=self.earlier,evidence_hash=h)
                self.rows[(key,action)].append(row);measured[key]=delta
                if delta!=(0,0):self.moved.add(key)
        self.earlier,self.previous=self.previous,action
        return measured
