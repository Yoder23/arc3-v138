from rope_physics_model_v2 import scene,step as source_all
from rope_physics_model_v4 import step as symmetric_all
from rope_physics_model_v6 import step as contact_enclosure
MODELS={'source_all':source_all,'symmetric_all':symmetric_all,'contact_enclosure':contact_enclosure}
def step(s,a,c):return MODELS[c.get('model','source_all')](s,a,c)
