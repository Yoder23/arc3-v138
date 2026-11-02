"""Observable stacked-bit command admission with unchanged parent fallback."""
from binary_rolling_program_v1 import Agent as Expert, bit_groups, target_scene
from binary_demonstration_bootstrap_v1 import components


def route(raw):
    if set(raw['available_actions'])!={6}:return 'parent'
    obs=components(raw['frame']);hs=[o for o in obs if o['box'][2:]==(1,3)];vs=[o for o in obs if o['box'][2:]==(3,1)]
    paired=[(a,b)for a in hs for b in vs if b['box'][:2]==(a['box'][0]+2,a['box'][1]+1)]
    values=sorted({o['ink']for pair in paired for o in pair})
    if len(paired)<3 or len(values)!=2:return 'parent'
    groups=bit_groups(raw['frame'],values)
    candidates=[ps for ps in groups.values()if len(ps)>=3 and target_scene(raw['frame'],ps)]
    return 'binary_animation'if len(candidates)==1 else 'parent'


class Controller:
    def __init__(self,parent):self.parent=parent;self.route=None;self.expert=None
    def respond(self,raw):
        if self.route is None:
            self.route=route(raw)
            if self.route=='binary_animation':self.expert=Expert()
        if self.route=='binary_animation':return self.expert.respond(raw)
        clean={k:raw[k]for k in ('frame','state','available_actions','levels_completed')}
        return self.parent.respond(clean)
