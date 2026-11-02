"""Tentatively plan with supported program hypotheses, reobserve after each action."""
from collections import deque
import copy
from parallel_model_learner_v1 import Learner as Base
from segmented_track_geometry_v1 import scenes,apply
from visual_transform_learner import public

class Learner(Base):
    def propose(self,raw):
        obs=public(raw)
        if obs['state']!='NOT_FINISHED' or 6 not in obs['available_actions']:return None
        for scene in scenes(obs['frame']):
            key=scene['cells'];goals=self.goals.get(key,[])
            if not goals or key in self.refuted or len(key)>255:continue
            inks=sorted({g['ink'] for g in goals});groups=[];start=[];target=[]
            for ink in inks:
                positions=[i for i,v in enumerate(scene['word']) if v==ink]
                if not positions:break
                groups.append((len(start),len(start)+len(positions)))
                start.extend(positions);target.append({g['index'] for g in goals if g['ink']==ink})
            else:
                if len(start)>24:continue
                models=[];seen_permutations=set()
                for control in scene['controls']:
                    model=self.models.get((key,control['point']))
                    if not model:continue
                    for permutation,shape in model['candidates'].items():
                        if permutation in seen_permutations:continue
                        seen_permutations.add(permutation)
                        inverse=[0]*len(permutation)
                        for destination,source in enumerate(permutation):inverse[source]=destination
                        descriptor=dict(control=control,permutation=permutation,**shape,support=model['support'])
                        models.append((inverse,descriptor))
                state=bytes(start);queue=deque([state]);previous={state:None};end=None
                while queue and len(previous)<=4096:
                    current=queue.popleft()
                    if current!=state and all(wanted.issubset(current[a:b]) for (a,b),wanted in zip(groups,target)):
                        end=current;break
                    for inverse,m in models:
                        values=[]
                        for a,b in groups:values.extend(sorted(inverse[p] for p in current[a:b]))
                        successor=bytes(values)
                        if successor not in previous:previous[successor]=(current,m);queue.append(successor)
                if end is None:continue
                route=[]
                while previous[end] is not None:end,m=previous[end];route.append(m)
                route.reverse();first=route[0];control=first['control']
                return dict(kind='track_conjunction_plan',action=6,data=dict(zip(('x','y'),control['point'])),
                    scene=copy.deepcopy(scene),goals=copy.deepcopy(goals),control=copy.deepcopy(control),route=copy.deepcopy(route),
                    predicted_word=apply(scene['word'],first['permutation']),tentative_goal=True,search_states=len(previous),
                    uncertainty='optimistic supported hypotheses; only first action executed before revision')
        return None
