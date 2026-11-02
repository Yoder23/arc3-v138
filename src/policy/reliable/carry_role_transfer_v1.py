"""Use a successful episode's observed appearance roles to resolve ambiguity."""
import copy
from carry_transport_learner_v10 import Controller as Base
from carry_affordance_geometry_v2 import scene

class Controller(Base):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.role_transfer=None
    def view(self,raw):
        v=super().view(raw)
        if v is not None or self.signature is not None:return v
        s=scene(raw['frame']);choices={}
        for old in self.episode_bank if self.retain else []:
            if (old['level']>=raw['levels_completed'] or not old['signature'] or not old['goal'] or len(old['motions'])<4):continue
            n,ink,fill,stripe=old['signature']
            bodies=[b for b in s['bodies'] if b['box'][2:]==(n,n) and b['fill_ink']==fill and b['stripe_ink']==stripe]
            cargo=[c for c in s['cargo'] if c['box'][2:]==(n,n) and c['inner_ink']==ink]
            if len(bodies)==1 and len(cargo)>=2:
                choices[tuple(old['signature'])]=(old,bodies[0])
        if len(choices)!=1:return None
        signature,(old,b)=next(iter(choices.items()));self.signature=signature
        self.phase=tuple(v%signature[0] for v in b['box'][:2])
        self.role_transfer=dict(level=raw['levels_completed'],observed_at=self.t,signature=signature,
            previous_episode=copy.deepcopy(old),hypothesis='retain_observed_role_after_actual_level_progress')
        return super().view(raw)
    def answer(self,raw,v,action,tag):
        response=super().answer(raw,v,action,tag)
        if self.role_transfer and self.role_transfer['level']==raw['levels_completed']:
            response['certificate']['role_transfer']=copy.deepcopy(self.role_transfer)
        return response
