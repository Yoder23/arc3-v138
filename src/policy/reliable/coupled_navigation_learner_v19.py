"""Track a selected object's connected shape even when its color also appears in the background."""
from coupled_navigation_learner_v18 import Agent as Prior
from structured_interaction_probe_v1 import parts
class Agent(Prior):
    def selected(self,obs,m):
        candidates=[(q['y'],q['x']) for q in parts(obs['frame']) if q['color']==m['selected_color'] and tuple(sorted(map(tuple,q['shape'])))==tuple(sorted(map(tuple,m['shape'])))]
        return candidates[0] if len(candidates)==1 else None
