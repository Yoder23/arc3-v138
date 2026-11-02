"""Preserve known miniature-lattice experts and allow adjacent corner marks."""
from parallel_context_learner_v3 import Controller as Base
from segmented_track_geometry_v1 import scenes
from nested_pattern_perception import representations
from visual_transform_learner import public

def isolated_mark_set(frame,goals):
    regions={}
    for g in goals:
        allowed=regions.setdefault(g['ink'],set())
        for y,x,h,w in g['marker_boxes']:
            allowed.update((a,b) for a in range(y,y+h) for b in range(x,x+w))
    height=len(frame);width=len(frame[0])
    for ink,pixels in regions.items():
        for y,x in pixels:
            for a,b in ((y-1,x),(y+1,x),(y,x-1),(y,x+1)):
                if 0<=a<height and 0<=b<width and (a,b) not in pixels and frame[a][b]==ink:return False
    return True

def admissible(obs):
    if obs['state']!='NOT_FINISHED' or 6 not in obs['available_actions']:return False
    scene=next((s for s in scenes(obs['frame']) if s['goals'] and s['controls']),None)
    return bool(scene and isolated_mark_set(obs['frame'],scene['goals']) and not representations(obs['frame']))

class Controller(Base):
    def respond(self,raw):
        obs=public(raw)
        if not self.active and self.prior is not None and not admissible(obs):
            assert self.learner.previous is None and not self.learner.history
            return self.prior.respond(obs)
        return super().respond(obs)
