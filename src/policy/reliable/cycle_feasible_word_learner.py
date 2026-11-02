"""Prefer program hypotheses supported by measured local control cycles."""
from collections import deque
import copy
from atomic_program_stagnation_learner import Learner as Base
from atomic_program_learner import program_key

class Learner(Base):
    def __init__(self):
        super().__init__()
        self.feasibility_revision=None

    def measured_domain(self,scene,index,legal):
        box=scene['box'];initial=scene['classes'][index]
        reached={initial};queue=deque([initial])
        while queue and len(reached)<=64:
            value=queue.popleft()
            for action in legal:
                model=self.effect(action,value,index,box)
                if model and model['after'] not in reached:
                    reached.add(model['after']);queue.append(model['after'])
        if queue or len(reached)>64:return reached,None
        # A closed cycle is evidence about this specific action at this index.
        # It is not proof that untested controls cannot reach other words.
        for action in legal:
            value=initial;seen={value};edges=[]
            for _ in range(64):
                model=self.effect(action,value,index,box)
                if not model or model['context']!='selected index':break
                edges.append(dict(action=action,before=value,**model));value=model['after']
                if value==initial:
                    if len(edges)>=2:return reached,dict(index=index,path=edges)
                    break
                if value in seen:break
                seen.add(value)
        return reached,None

    def observe(self,obs,action=None):
        super().observe(obs,action);self.feasibility_revision=None
        if not self.active or not self.scenes or obs['state']!='NOT_FINISHED':return
        legal=sorted(set(obs['available_actions'])&{1,2,3,4,5,7})
        cache={}
        def profile(scene):
            witnesses=[]
            for i,target in enumerate(scene['expected']):
                if target==scene['classes'][i]:continue
                key=(scene['box'],i,scene['classes'][i])
                if key not in cache:cache[key]=self.measured_domain(scene,i,legal)
                reached,cycle=cache[key]
                if cycle and target not in reached:
                    witnesses.append(dict(cycle,target=target))
            return witnesses
        prior=self.snapshot;old_profile=profile(prior)
        if not old_profile:return
        chosen=min(self.scenes,key=lambda s:(
            self.failed_goals[program_key(s)],len(profile(s)),
            int(self.choice is not None and self.choice!=program_key(s)),s['source_box'],
            sum(x!=y for x,y in zip(s['classes'],s['expected'])),s['expected']))
        new_profile=profile(chosen)
        if len(new_profile)>=len(old_profile):return
        self.snapshot=chosen
        self.feasibility_revision=dict(
            previous_expected=prior['expected'],previous_cycles=old_profile,
            chosen_cycles=new_profile,
            scope='Prioritize fewer targets outside measured control cycles. Other controls and the goal interpretation remain unconfirmed.')

    def propose(self,obs):
        c=super().propose(obs)
        return dict(c,feasibility_revision=copy.deepcopy(self.feasibility_revision)) if c and self.feasibility_revision else c
