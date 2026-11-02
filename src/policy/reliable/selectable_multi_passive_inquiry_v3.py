"""When all outlined goal hypotheses are occupied but the task continues, test another object class."""
from selectable_multi_passive_inquiry_v2 import Agent as Base
class Agent(Base):
    def joint_response(self,raw):
        if 2<=len(self.objects)<=4 and self.shape_goals and all(any(tuple(b['box'][:2])==(g['box'][0]+1,g['box'][1]+1) and tuple(g['box'][2:])==(b['box'][2]+2,b['box'][3]+2) for g in self.goals) for b in self.objects):return dict(done=True,action=None,data={})
        return super().joint_response(raw)
