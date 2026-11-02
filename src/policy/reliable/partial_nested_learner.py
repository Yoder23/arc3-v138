"""Reuse demonstrated local relations beyond a complete eight-neighbor parser."""
import copy
from nested_constraint_learner_v2 import Learner as Prior
from partial_nested_perception import expanded
from visual_transform_learner import public

class Learner(Prior):
    def observe(self,raw,last=None,data=None):
        # Failure of a partial interpretation is not a refutation of the
        # learned global relation. Preserve its scope and the actual episode.
        if self.pending and self.pending.get('kind')=='partial_nested_constraint':self.pending=None
        super().observe(raw,last,data)

    def propose(self,raw):
        obs=public(raw)
        if obs['state']=='NOT_FINISHED' and 6 in obs['available_actions']:
            for p in expanded(obs['frame'],self.memory):
                m=p['memory'];con={(r['y'],r['x']):r for r in p['constraints']}
                samples=[s for s in self.samples if s['row']>=self.level_start and s['row'] in self.safe_sample_rows]
                palette=sorted({v for y,x,v in p['cells']}|{q['pattern'][1][1] for q in p['markers']}|{s[k] for s in samples for k in ('old','new')})
                desired={};choices=[]
                for y,x,color in p['cells']:
                    req=con[y,x];legal=[v for v in palette if (not req['equal'] or v in req['equal']) and v not in req['unequal']]
                    goal=color if color in legal else min(legal) if legal else None
                    desired[y,x]=goal
                    if goal!=color:choices.append((self.visits[self.level,y,x],y,x,color,goal))
                if not choices:continue
                _,y,x,color,goal=min(choices);size=p['size']
                return dict(kind='partial_nested_constraint',action=6,data=dict(x=x+size//2,y=y+size//2),
                    source=m['source'],examples=copy.deepcopy(m['examples']),rule=tuple(m['rule']),
                    scene=copy.deepcopy({k:v for k,v in p.items() if k!='memory'}),
                    palette=palette,palette_evidence=[copy.deepcopy(self.rows[s['row']]) for s in samples],
                    desired=[(y,x,v) for (y,x),v in sorted(desired.items())],box=(y,x,size,size),old=color,expected=goal,
                    scope='Apply only the two interpreted inks learned from visible examples to uniform neighboring cells on an observed lattice. Additional inks and nonuniform neighbors are uninterpreted. This is a partial goal hypothesis; actual progress is required to establish sufficiency.')
        return super().propose(obs)
