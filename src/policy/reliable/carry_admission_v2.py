"""Choose the carry expert once from a complete visible scene; preserve its parent."""
from carry_interaction_learner_v6 import Controller as Base
from visual_transform_learner import public
from carry_affordance_geometry_v2 import scene

def admissible(obs):
    if obs['state']!='NOT_FINISHED' or set(obs['available_actions'])!=set(range(1,6)):
        return False
    probe=Base();v=probe.view(obs)
    if v is not None:return len(v['containers'])==1 and 2<=len(v['cargo'])<=12
    # Adjacent cargo can resemble a second stripe. A repeated object lattice
    # may still identify one geometrically compatible body. This only admits
    # the expert; its unchanged perception must resolve identity from data.
    s=scene(obs['frame'])
    identities={(c['box'][2],c['inner_ink']) for c in s['cargo']}
    for n,ink in sorted(identities):
        objects=[c for c in s['framed'] if c['box'][2:]==(n,n) and c['inner_ink']==ink]
        if not 2<=len(objects)<=12:continue
        phases={(c['box'][0]%n,c['box'][1]%n) for c in objects}
        if len(phases)!=1:continue
        bodies=[b for b in s['bodies'] if b['box'][2:]==(n,n) and (b['box'][0]%n,b['box'][1]%n) in phases]
        regions=[c for c in s['containers'] if len(objects)*n*n<=c['box'][2]*c['box'][3]<=2*len(objects)*n*n and c['box'][2]%n==c['box'][3]%n==0]
        if len(bodies)==len(regions)==1:return True
    return False

class Controller(Base):
    def __init__(self,prior=None,retain=True):
        super().__init__(prior,retain);self.admission_checked=False;self.admitted=False
    def respond(self,raw):
        obs=public(raw)
        if not self.admission_checked and obs['state']=='NOT_FINISHED':
            self.admitted=admissible(obs);self.admission_checked=True
        if not self.admitted and self.prior is not None:
            return self.prior.respond(obs)
        return super().respond(obs)
