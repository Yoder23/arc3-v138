"""Admit a single visible outlined body when a compatible goal frame is present."""
from selectable_multi_object_learner_v23 import Agent as Base
from selectable_rect_geometry_v1 import rings
class Agent(Base):
    def observe(self,raw):
        if self.palette is None:
            rs=rings(raw['frame']);bodies=[r for r in rs if r.get('tile_body')]
            if len(bodies)==1:
                b=bodies[0]
                if any(g['ink']!=b['ink'] and tuple(g['box'][2:])==(b['box'][2]+2,b['box'][3]+2) for g in rs):self.palette=b['ink'];self.size=b['box'][2]
        return super().observe(raw)
