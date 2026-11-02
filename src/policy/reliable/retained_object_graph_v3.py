"""Treat terminal attempts as revisable context evidence, not permanent bans."""
from retained_object_graph_v2 import Learner as Base
from retained_object_graph import state

class Learner(Base):
    def __init__(self,**kwargs):
        super().__init__(**kwargs);self.terminal_contexts={}

    def observe(self,raw,action=None,data=None):
        super().observe(raw,action,data)
        latest={}
        for i,e in enumerate(self.history):
            if e['before']['state']=='NOT_FINISHED' and e['after']['state']=='GAME_OVER':
                latest[state(e['before'],self.features),e['action']]=i
        self.terminal_contexts=latest;reliable={}
        for (a,action),outcomes in self._outcomes.items():
            if len(outcomes)!=1:continue
            b,rows=next(iter(outcomes.items()))
            support=[i for i in rows if i>latest.get((a,action),-1)]
            if b!=a and support:reliable[a,action]=(b,support[0])
        # A terminal pair can be experimentally retried. Until a subsequent
        # successful observation, it cannot support a planned route.
        self._graph=(reliable,self._attempts,set(),sum(len(v)>1 for v in self._outcomes.values()))
