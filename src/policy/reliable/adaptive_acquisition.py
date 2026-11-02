"""End shared acquisition when a unique supported control model is available."""
from compound_planner import CompoundPlanner

class AdaptivePlanner(CompoundPlanner):
    def __init__(self,*,adaptive=True,minimum_acquisition=16,**kwargs):
        super().__init__(**kwargs);self.adaptive_enabled=adaptive;self.minimum_acquisition=minimum_acquisition

    def choose(self,obs):
        old_warmup=self.warmup;ready=False
        if self.adaptive_enabled and self.minimum_acquisition<=self.action_count<old_warmup:
            nominees=[]
            for sig,part in self.temporal.parts(obs).items():
                if sig not in self.temporal.moved:continue
                models=self.models(sig)
                if models:nominees.append((sig,part,models))
            nominees=self.select_nominees(nominees,obs)
            ready=len(nominees)==1
            if ready:self.warmup=0
        try:result=super().choose(obs)
        finally:self.warmup=old_warmup
        self.decisions[-1]['adaptive_acquisition_ready']=ready
        self.decisions[-1]['minimum_acquisition_actions']=self.minimum_acquisition
        return result

    def run(self,initial,step,*,max_actions=256):
        result=super().run(initial,step,max_actions=max_actions)
        result['temporal_model_grammar']='evidence_ready_acquisition_with_connected_action_models'
        return result

