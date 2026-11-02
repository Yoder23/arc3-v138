"""When an unconfirmed control is blocked, test it with another visible body."""
from selectable_rect_identity_v2 import Agent as Base
class Agent(Base):
    def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self.conditional_inquiries={}
    def joint_response(self,raw):
        missing=[a for a in (1,2,3,4) if a in raw['available_actions'] and a not in self.motions]
        if missing:
            bodies=sorted(self.objects,key=lambda b:(tuple(b['box'])!=tuple(self.active_box or ()),self.identities[tuple(b['box'])]))
            for body in bodies:
                ident=self.identities[tuple(body['box'])]
                for a in missing:
                    key=(self.level,ident,tuple(body['box']),a)
                    if key in self.conditional_inquiries:continue
                    if tuple(body['box'])!=tuple(self.active_box or ()):
                        y,x,h,w=body['box'];return self.answer(raw,6,dict(x=x+w//2,y=y+h//2),'joint_select_control_probe',body,[a])
                    self.conditional_inquiries[key]=self.t
                    return self.answer(raw,a,{},'joint_inquire_unconfirmed_control')
        return super().joint_response(raw)
