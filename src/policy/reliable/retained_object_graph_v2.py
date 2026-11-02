"""Incremental observed graph; populate caches during observation, not proposal."""
from collections import Counter,defaultdict
from retained_object_graph import Learner as Base,state

class Learner(Base):
    def __init__(self,**kwargs):
        super().__init__(**kwargs);self._features=None;self._consumed=0
        self._outcomes={};self._attempts=Counter();self._failures=set()

    def observe(self,raw,action=None,data=None):
        old=self.previous
        cleared=old is not None and (raw['levels_completed']!=old['levels_completed'] or raw['state']=='WIN'
            or action==0 and not self.retain)
        super().observe(raw,action,data)
        if cleared or self._features!=self.features:
            self._features=self.features;self._consumed=0;self._outcomes={}
            self._attempts=Counter();self._failures=set()
        for i in range(self._consumed,len(self.history)):
            e=self.history[i]
            if e['before']['state']!='NOT_FINISHED' or e['action'] not in (1,2,3,4,5,7):continue
            a=state(e['before'],self.features);b=state(e['after'],self.features);key=(a,e['action'])
            self._attempts[key]+=1
            if e['after']['state']=='GAME_OVER':self._failures.add(key)
            elif e['after']['state']=='NOT_FINISHED':
                outcomes=self._outcomes.setdefault(key,{})
                outcomes.setdefault(b,[]).append(i)
        self._consumed=len(self.history);reliable={}
        for (a,action),outcomes in self._outcomes.items():
            if len(outcomes)==1 and (a,action) not in self._failures:
                b,rows=next(iter(outcomes.items()))
                if a!=b:reliable[a,action]=(b,rows[0])
        self._graph=(reliable,self._attempts,self._failures,sum(len(v)>1 for v in self._outcomes.values()))
