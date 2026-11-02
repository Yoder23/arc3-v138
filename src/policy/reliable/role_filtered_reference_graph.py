"""Use retained visible reference hypotheses to prioritize graph experiments."""
from collections import Counter,deque
from itertools import permutations
from fractions import Fraction
import copy
from retained_object_graph_v3 import Learner as Base
from retained_object_graph import groups,state
from visual_transform_learner import public,digest

def distance(poses,target):
    if len(poses)!=len(target) or not poses:return None
    return min(sum(abs(y-u)+abs(x-v) for (y,x),(u,v) in zip(poses,p)) for p in permutations(target))

def route_units(graph,features):
    units={key:(1,None) for key in features}
    measured=set()
    for (old,action),(new,row) in graph.items():
        left,right=dict(old),dict(new)
        for key in features:
            d=distance(left.get(key,()),right.get(key,()))
            if d is not None and d>0:
                if key not in measured or d>units[key][0] or d==units[key][0] and row<units[key][1]:
                    units[key]=(d,row);measured.add(key)
    return units

class Learner(Base):
    def __init__(self,**kwargs):
        super().__init__(**kwargs);self.references={};self.failed_references=set();self.reference_features=()

    def observe(self,raw,action=None,data=None):
        obs=public(raw);prior=self.previous;old_pending=self.pending
        boundary=prior is not None and (obs['levels_completed']!=prior['levels_completed'] or obs['state']=='WIN' or action==0 and not self.retain)
        super().observe(obs,action,data)
        if boundary:
            self.references={};self.failed_references=set();self.reference_features=()
        if old_pending and old_pending.get('reference_hypothesis') and prior and prior['state']==obs['state']=='NOT_FINISHED' and prior['levels_completed']==obs['levels_completed']:
            ref=old_pending['reference_hypothesis']
            if groups(obs).get(ref['feature'])==ref['target_poses']:
                self.failed_references.add(ref['id'])
        scans=[(len(self.history),obs)]
        if self.features!=self.reference_features:
            scans=[(i,e['before']) for i,e in enumerate(self.history)]+scans
            self.reference_features=self.features
        for index,frame in scans:
            seen=groups(frame)
            for key in self.features:
                for other,poses in seen.items():
                    if other==key or other in self.features or other[1]!=key[1] or len(poses)!=len(seen.get(key,())):continue
                    identity=digest((key,other,poses))
                    if identity not in self.references and len(self.references)<32:
                        self.references[identity]=dict(id=identity,feature=key,reference=other,target_poses=poses,observed_at=index)

    def propose(self,raw):
        obs=public(raw)
        if obs['state']!='NOT_FINISHED' or not self.features:return None
        legal=tuple(sorted(set(obs['available_actions'])&{1,2,3,4,5,7}))
        refs=[r for k,r in self.references.items() if k not in self.failed_references and r['feature'] in self.features and r['reference'] not in self.features]
        if not refs or not legal:return super().propose(obs)
        here=state(obs,self.features)
        if not any(poses for key,poses in here):return None
        graph,attempts,failures,conflicts=self.graph();units=route_units(graph,self.features);queue=deque([(here,[])]);seen={here};options=[]
        global_counts=Counter()
        for (s,a),n in attempts.items():global_counts[a]+=n
        while queue and len(seen)<=2048:
            s,path=queue.popleft();positions=dict(s);targets=[]
            for r in refs:
                d=distance(positions.get(r['feature'],()),r['target_poses'])
                if d is not None:
                    unit,row=units[r['feature']]
                    targets.append((Fraction(d,unit)+len(path),d,r['id'],r,unit,row))
            nearest=min(targets,key=lambda v:v[:3]) if targets else None
            for a in legal:
                if (s,a) not in failures and nearest:
                    options.append((attempts[s,a],nearest[0],len(path),global_counts[a],a,repr(s),path,s,nearest[3],nearest[1],nearest[4],nearest[5]))
                edge=graph.get((s,a))
                if edge and edge[0] not in seen and len(path)<48:
                    seen.add(edge[0]);queue.append((edge[0],path+[dict(action=a,row=edge[1])]))
        if not options:return super().propose(obs)
        trials,priority,_,_,probe,_,path,target,ref,d,unit,unit_row=min(options,key=lambda v:v[:6])
        used=sorted({edge['row'] for edge in path}|({unit_row} if unit_row is not None else set()))
        return dict(kind='retained_object_frontier',action=path[0]['action'] if path else probe,data={},context=digest(obs),
            features=self.features,current=here,target=target,path=path,probe_action=probe,prior_probe_attempts=trials,
            projection_conflicts=conflicts,feature_support={digest(k):self.motion[k][:] for k in self.features},
            evidence=[dict(index=i,**copy.deepcopy(self.history[i])) for i in used],
            reference_hypothesis=copy.deepcopy(ref),reference_distance=d,route_step_unit=unit,route_unit_source_row=unit_row,
            reference_route_cost=dict(numerator=d+unit*len(path),denominator=unit),
            scope='Observed congruent reference is a tentative alignment goal. Known route length plus reference distance scaled by an actually observed joint displacement orders equally tested frontiers; only actual outcomes can confirm or refute the hypothesis.')
