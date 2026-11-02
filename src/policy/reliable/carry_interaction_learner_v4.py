"""Retain a rectangular packing hypothesis without assuming complete occupancy."""
from carry_interaction_learner_v3 import Controller as Base
from carry_affordance_geometry_v2 import scene

class Controller(Base):
    def view(self, raw):
        v = super().view(raw)
        if v is None:
            return None
        n = v['n']; count = len(v['cargo'])
        # A visually framed region may have spare cells or span two dimensions.
        # This admits a tentative region; actual progress remains the only reward.
        v['containers'] = [c for c in scene(raw['frame'])['containers']
                           if count*n*n <= c['box'][2]*c['box'][3] <= 2*count*n*n
                           and c['box'][2] % n == c['box'][3] % n == 0]
        return v
