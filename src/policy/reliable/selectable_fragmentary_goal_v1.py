"""Keep a partially visible frame as a goal hypothesis and verify it through actions."""
from selectable_controller_handoff_v1 import Agent as Base
from selectable_rect_geometry_v1 import rings
from fragmentary_goal_geometry_v1 import goals
class Agent(Base):
    def observe(self,raw):
        rs=rings(raw['frame']);bodies=[r for r in rs if r.get('tile_body')]
        if self.palette is None and len(bodies)==1:
            b=bodies[0];gs=goals(raw['frame'],b)
            if gs:self.palette=b['ink'];self.size=b['box'][2]
        result=super().observe(raw)
        if result and not self.goals and len(self.objects)==1:
            self.goals=[dict(g,observed_at=self.t) for g in goals(raw['frame'],self.objects[0])]
        return result
