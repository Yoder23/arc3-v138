"""Generalize binary examples into equality constraints; discover missing colors."""
from collections import defaultdict
import copy
import numpy as np
from nested_pattern_learner import Learner as Binary
from nested_pattern_perception import representations
from visual_transform_learner import public

def constraints(scene,rule):
    ink,flip,turn=rule;result=defaultdict(lambda:dict(equal=set(),unequal=set()))
    for m in scene['markers']:
        pattern=np.asarray(m['pattern'])
        pattern=np.rot90(np.fliplr(pattern) if flip else pattern,turn)
        center=int(pattern[1,1])
        if ink not in {int(pattern[y,x]) for y in range(3) for x in range(3) if (y,x)!=(1,1)}:return None
        for (y,x),pos in zip([(y,x) for y in range(3) for x in range(3) if (y,x)!=(1,1)],m['neighbors']):
            result[pos]['equal' if int(pattern[y,x])==ink else 'unequal'].add(center)
    if any(len(v['equal'])>1 or v['equal']&v['unequal'] for v in result.values()):return None
    return {pos:dict(equal=sorted(v['equal']),unequal=sorted(v['unequal'])) for pos,v in result.items()}

class Learner(Binary):
    def __init__(self):
        super().__init__();self.constraint_scenes=[];self.level_start=0;self.safe_sample_rows=set()

    def observe(self,raw,last=None,data=None):
        obs=public(raw)
        if self.previous is not None and obs['levels_completed']!=self.previous['levels_completed']:
            self.level_start=len(self.rows)+int(last is not None)
        before=self.previous
        valid=before is not None and last==6 and before['state']==obs['state']=='NOT_FINISHED' and before['levels_completed']==obs['levels_completed']
        super().observe(raw,last,data)
        if valid:self.safe_sample_rows.add(len(self.rows)-1)
        self.constraint_scenes=[]
        if not self.current and obs['state']=='NOT_FINISHED':
            for scene in representations(obs['frame']):
                for m in self.memory:
                    con=constraints(scene,m['rule'])
                    if con is not None:self.constraint_scenes.append((scene,m,con))

    def propose(self,raw):
        old=super().propose(raw)
        if old or self.current:return old
        obs=public(raw)
        if obs['state']!='NOT_FINISHED' or 6 not in obs['available_actions']:return None
        for scene,m,con in self.constraint_scenes:
            if tuple(m['rule']) in self.failed:continue
            samples=[s for s in self.samples if s['row']>=self.level_start and s['row'] in self.safe_sample_rows]
            palette=sorted({v for y,x,v in scene['cells']}|{p['pattern'][1][1] for p in scene['markers']}|
                           {s[k] for s in samples for k in ('old','new')})
            desired={};choices=[]
            for y,x,color in scene['cells']:
                c=con[y,x];legal=[v for v in palette if (not c['equal'] or v in c['equal']) and v not in c['unequal']]
                goal=color if color in legal else (min(legal) if legal else None)
                desired[y,x]=goal
                if color!=goal:choices.append((self.visits[self.level,y,x],y,x,color,goal))
            if not choices:continue
            _,y,x,color,goal=min(choices);support=[];origins=set()
            relevant=[s for s in samples if s['old']==color]
            destinations={s['new'] for s in relevant}
            if len(destinations)==1:
                for s in relevant:
                    if tuple(s['box'][:2]) not in origins:
                        origins.add(tuple(s['box'][:2]));support.append(s['row'])
                    if len(support)==2:break
            if len(support)!=2:support=[]
            size=scene['size']
            return dict(kind='nested_constraint',action=6,data=dict(x=x+size//2,y=y+size//2),
                source=m['source'],examples=copy.deepcopy(m['examples']),rule=tuple(m['rule']),
                scene=copy.deepcopy(scene),constraints=[dict(y=y,x=x,**v) for (y,x),v in sorted(con.items())],
                palette=palette,palette_evidence=[copy.deepcopy(self.rows[s['row']]) for s in samples],
                desired=[(y,x,v) for (y,x),v in sorted(desired.items())],box=(y,x,size,size),
                old=color,expected=goal,expected_next=next(iter(destinations)) if support else None,
                control_mode='learned_color_transition' if support else 'uncertain_probe',
                control_support=support,control_evidence=[copy.deepcopy(self.rows[i]) for i in support])
        return None
