"""Version-space probe over one-step and persistent two-state action contexts.

Modes are generic hypotheses over every observed action identifier. A mode is
admitted only with a matched-position effect contrast and compatible historical
motion evidence. No environment identity, configured controls or actor labels.
"""
from collections import defaultdict
from temporal_effect_memory import Memory as BaseMemory,visible

class Memory(BaseMemory):
    def __init__(self,contextual):super().__init__(False);self.contextual=contextual;self.parity=defaultdict(int)
    def observe(self,before,action,after):
        lengths={k:len(v) for k,v in self.rows.items()};result=super().observe(before,action,after)
        for k,rows in self.rows.items():
            for row in rows[lengths.get(k,0):]:row['parity_before']=dict(self.parity)
        self.parity[action]^=1;return result
    def predict(self,before,action):
        # Preserve every unchanged global prediction and all its failure cases.
        contextual=self.contextual;self.contextual=False
        try:out=super().predict(before,action)
        finally:self.contextual=contextual
        if not contextual:return out
        present={(r['label'],tuple(tuple(p) for p in r['shape_rc'])) for r in out}
        for signature,part in self.parts(before).items():
            if signature not in self.moved or signature in present:continue
            history=[(a,r) for (sig,a),rows in self.rows.items() if sig==signature for r in rows]
            actions=sorted({a for a,r in history});supported=[]
            for kind in ('previous_action','persistent_toggle'):
                for trigger in actions:
                    mode=lambda r: int(r['previous']==trigger) if kind=='previous_action' else r['parity_before'].get(trigger,0)
                    current=int(self.previous==trigger) if kind=='previous_action' else self.parity[trigger]
                    effects=defaultdict(list);position=defaultdict(lambda:defaultdict(set))
                    for a,r in history:
                        q=mode(r);effects[(q,a)].append(r)
                        if r['delta']!=(0,0):position[(r['origin'],a)][q].add(r['delta'])
                    if any(len({r['delta'] for r in rows if r['delta']!=(0,0)})>1 for rows in effects.values()):continue
                    contrasts=[dict(origin_rc=list(p),action=a,effects=[list(next(iter(v[q]))) for q in (0,1)])
                        for (p,a),v in position.items() if len(v)==2 and all(len(v[q])==1 for q in (0,1)) and v[0]!=v[1]]
                    if not contrasts:continue
                    rows=effects.get((current,action),[]);moving=[r for r in rows if r['delta']!=(0,0)];values={r['delta'] for r in moving}
                    origin=tuple(part['origin_rc'])
                    # A supported model with an unobserved current effect must
                    # remain in the version space as explicit uncertainty.
                    delta=next(iter(values)) if len(values)==1 and len(moving)>=2 and len({r['origin'] for r in moving})>=2 else None
                    if delta is not None and any(r['origin']==origin and r['delta']!=delta for r in rows):delta=None
                    supported.append(dict(kind=kind,trigger=trigger,state=current,delta=delta,rows=moving,contrasts=contrasts))
            if not supported or any(h['delta'] is None for h in supported) or len({h['delta'] for h in supported})!=1:continue
            delta=supported[0]['delta']
            out.append(dict(label=signature[0],shape_rc=[list(p) for p in signature[1]],origin_rc=part['origin_rc'],delta_rc=list(delta),
                status='latent_action_context',previous_action=self.previous,
                hypotheses=[dict(kind=h['kind'],trigger_action=h['trigger'],current_state=h['state'],matched_position_contrasts=h['contrasts']) for h in supported],
                support=sorted({r['evidence_hash'] for h in supported for r in h['rows']}),
                assumptions=['authored two-state context grammar','stable unique visible appearance','unblocked effect at unseen origin','observational contrasts do not establish causality']))
        return out
