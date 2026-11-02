"""Use a fully measured binary model consistently across successive actions."""
import copy
from decorated_lattice_learner_v2 import Learner as Base,layout,read_variables,action_models
from visual_transform_learner import public
from binary_effect_planner_v1 import plan

class Learner(Base):
    def propose(self,raw):
        obs=public(raw)
        if obs['state']!='NOT_FINISHED' or 6 not in obs['available_actions']:return None
        scene=layout(obs['frame'],self.memory)
        if not scene or 'decorations' not in scene or len(scene['palette'])!=2:return super().propose(raw)
        current=read_variables(obs['frame'],scene)
        if current is None:return super().propose(raw)
        models=action_models(self.effects,obs['levels_completed'],scene['palette'])
        structured=[(v['y'],v['x']) for v in scene['variables'] if v['structured']]
        if any(p not in models or not models[p]['ready'] for p in structured):return super().propose(raw)
        allowed={(c['y'],c['x']):[v for v in scene['palette'] if (not c['equal'] or v in c['equal']) and v not in c['unequal']] for c in scene['constraints']}
        sequence=plan(current,allowed,models,scene['palette'])
        if not sequence:return super().propose(raw)
        point=sequence[0];y,x=point;m=models[point];support=m['support']
        def evidence(p):
            ids=models[p]['support']
            return dict(point=p,support=ids,evidence=[copy.deepcopy(e) for e in self.effects if e['row'] in ids])
        return dict(kind='decorated_lattice',phase='plan',action=6,data=dict(x=x+scene['size']//2,y=y+scene['size']//2),
            box=(y,x,scene['size'],scene['size']),scene=copy.deepcopy(scene),support=support,
            evidence=evidence(point)['evidence'],forecast=[(yy,xx,d[current[yy,xx]]) for (yy,xx),d in m['transitions'].items()],
            plan=sequence,binary_composition=dict(models=[evidence(p) for p in sequence]),
            scope='Tentative composition of actual complete binary swap cycles. Every selected action has earlier observed witnesses. Gaussian elimination proposes parities; observed outcomes still determine progress and replanning.')
