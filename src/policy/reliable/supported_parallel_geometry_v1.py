"""Attach explicit compositional programs to hypotheses supported by actual effects."""
from parallel_track_programs_v1 import hypotheses
from segmented_track_geometry_v1 import scenes,apply,read

def permutations(scene):
    cells=scene['cells'];radius=max((a[0]-b[0])**2+(a[1]-b[1])**2 for a in cells for b in cells)
    return {p:dict(shape,mapping='observed_global_correspondence',radius_squared=radius) for p,shape in hypotheses(scene).items()}
