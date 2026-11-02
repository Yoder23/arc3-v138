"""Receding-horizon planning over evidence-supported latent control contexts.

The model grammar, component perception, and contact-goal prior are authored.
All displacement tables and context selection use actual pixel transitions.
Planning changes hypothetical mode bits, never the observational evidence.
"""
from collections import defaultdict, deque
from composite_components import palette
from copy import deepcopy
import random
from learner import ReliableLearner
from evidence import observation, primitive_components, digest
from temporal_effect_memory import visible
from temporal_effect_memory_v4 import Memory


class TemporalPlanner(ReliableLearner):
    def __init__(self, *, temporal=True, warmup=96, schedule_seed=0):
        super().__init__()
        self.temporal_enabled=temporal
        self.temporal=Memory(True)
        self.warmup=warmup
        self.schedule_seed=schedule_seed
        self.decisions=[]
        self.temporal_rejections=set()

    def select_nominees(self,nominees,obs):
        return nominees

    def models(self, signature):
        history=[(a,r) for (sig,a),rows in self.temporal.rows.items() if sig==signature for r in rows]
        models=[]
        for kind in ('previous_action','persistent_toggle'):
            for trigger in sorted({a for a,r in history}):
                mode=lambda r: int(r['previous']==trigger) if kind=='previous_action' else r['parity_before'].get(trigger,0)
                effects=defaultdict(list); positions=defaultdict(lambda:defaultdict(set)); action_contrasts=defaultdict(lambda:defaultdict(set))
                for a,r in history:
                    q=mode(r);effects[(q,a)].append(r)
                    if r['delta']!=(0,0):positions[(r['origin'],a)][q].add(r['delta'])
                    action_contrasts[(r['origin'],q)][a].add(r['delta'])
                if any(len({r['delta'] for r in rows if r['delta']!=(0,0)})>1 for rows in effects.values()):continue
                contrasts=[(p,a) for (p,a),v in positions.items() if len(v)==2 and all(len(v[q])==1 for q in (0,1)) and v[0]!=v[1]]
                controls=[p for (p,q),v in action_contrasts.items() if len({next(iter(ds)) for ds in v.values() if len(ds)==1})>=2]
                if not contrasts or len(set(controls))<2:continue
                table={};support={};locals_={}
                for (q,a),rows in effects.items():
                    moving=[r for r in rows if r['delta']!=(0,0)]
                    evidence=moving or rows
                    values={r['delta'] for r in evidence}
                    if len(values)==1 and len(evidence)>=2 and len({r['origin'] for r in evidence})>=2:
                        table[(q,a)]=next(iter(values));support[(q,a)]=sorted({r['evidence_hash'] for r in evidence})
                    for r in rows:locals_.setdefault((q,a,r['origin']),set()).add(r['delta'])
                state=int(self.temporal.previous==trigger) if kind=='previous_action' else self.temporal.parity[trigger]
                models.append(dict(kind=kind,trigger=trigger,state=state,table=table,support=support,local=locals_,contrasts=contrasts))
        return models

    @staticmethod
    def transition(models, modes, origin, action):
        deltas=[];supports=[];after=[]
        for m,q in zip(models,modes):
            d=m['table'].get((q,action))
            if d is None:return None
            if any(old!=d for old in m['local'].get((q,action,origin),set())):return None
            deltas.append(d);supports.extend(m['support'][(q,action)])
            after.append(int(action==m['trigger']) if m['kind']=='previous_action' else q^int(action==m['trigger']))
        if not deltas or len(set(deltas))!=1:return None
        return deltas[0],tuple(after),sorted(set(supports))

    def temporal_route(self, obs, part, models, target):
        origin=tuple(part['origin_rc']);mode=tuple(m['state'] for m in models);start=(origin,mode)
        key=(part['label'],tuple(tuple(p) for p in part['shape_rc']))
        floor=self.temporal.vacated_labels[key]
        # Entering the candidate target is an explicit contact-goal experiment.
        allowed=floor|palette(part['label'])|{target['label']};frame=obs['frame'];shape=part['shape_rc']
        target_cells={tuple(p) for p in target['cells_rc']}
        queue=deque([(start,[])]);seen={start}
        while queue and len(seen)<=1024:
            (p,qs),path=queue.popleft()
            if any((p[0]+y,p[1]+x) in target_cells for y,x in shape):return path
            if len(path)>=24:continue
            for a in obs['available_actions']:
                effect=self.transition(models,qs,p,a)
                if effect is None:continue
                (dy,dx),nq,support=effect;np=(p[0]+dy,p[1]+dx);state=(np,nq)
                if state in seen:continue
                if not all(0<=np[0]+y<len(frame) and 0<=np[1]+x<len(frame[0]) and frame[np[0]+y][np[1]+x] in allowed for y,x in shape):continue
                seen.add(state);queue.append((state,path+[dict(action=a,origin_rc=list(p),delta_rc=[dy,dx],modes_before=list(qs),modes_after=list(nq),support=support)]))
        return None

    def choose(self, obs):
        record=dict(step=self.action_count,temporal=False)
        if self.action_count<self.warmup:
            rng=random.Random(self.schedule_seed+self.action_count)
            result=(rng.choice(obs['available_actions']),None,'shared_context_acquisition')
        else:
            options=[];nominees=[]
            if self.temporal_enabled:
                for signature,part in self.temporal.parts(obs).items():
                    if signature not in self.temporal.moved:continue
                    models=self.models(signature)
                    if models:nominees.append((signature,part,models))
                nominees=self.select_nominees(nominees,obs)
                if len(nominees)==1:
                    sig,part,models=nominees[0]
                    floor=self.temporal.vacated_labels[sig];total=len(obs['frame'])*len(obs['frame'][0])
                    for target in primitive_components(obs['frame']):
                        if target['label'] in floor|palette(part['label']) or target['size']>=total/4:continue
                        if (target['label'],tuple(target['origin_rc'])) in self.temporal_rejections:continue
                        path=self.temporal_route(obs,part,models,target)
                        if path==[]:self.temporal_rejections.add((target['label'],tuple(target['origin_rc'])))
                        elif path:options.append((len(path),path[0]['action'],target,path,part,models))
            if options:
                _,action,target,path,part,models=min(options,key=lambda r:(r[0],r[1]))
                prediction=dict(label=part['label'],shape_rc=part['shape_rc'],delta_rc=path[0]['delta_rc'])
                result=(action,prediction,'test_temporal_object_contact')
                record.update(temporal=True,actor=dict(label=part['label'],shape_rc=part['shape_rc']),target=target,
                    path=path,models=[dict(kind=m['kind'],trigger=m['trigger'],current_state=m['state']) for m in models],
                    assumptions=['stable conditional effects','vacated surface labels predict traversability','target contact may be a goal'])
            else:result=super().choose(obs)
        record.update(action=result[0],prediction=result[1],purpose=result[2]);self.decisions.append(record)
        return result

    def run(self, initial, step, *, max_actions=256):
        current=observation(initial)
        def observe_step(action):
            nonlocal current
            after=observation(step(action))
            if after['levels_completed']!=current['levels_completed'] or after['state']!='NOT_FINISHED':
                vision=self.temporal.parts;self.temporal=type(self.temporal)(True);self.temporal.parts=vision;self.temporal_rejections.clear()
            else:self.temporal.observe(current,action,after)
            current=after
            return after
        out=super().run(initial,observe_step,max_actions=max_actions)
        out['temporal_decisions']=deepcopy(self.decisions)
        out['temporal_actions']=sum(d['temporal'] for d in self.decisions)
        out['temporal_model_grammar']='previous_action_or_persistent_toggle'
        return out
