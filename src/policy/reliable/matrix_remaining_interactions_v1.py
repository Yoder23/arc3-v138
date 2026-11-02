"""An observed local effect does not settle other visible interaction targets."""
from matrix_size_precondition_v4 import Agent as Base
from matrix_reference_programs_v1 import programs
from matrix_reference_cues_v2 import cues
from matrix_motion_learner_v6 import objects
from matrix_intermediate_learner_v3 import gap
class Agent(Base):
 def reference_targets(self,raw):
  if not self.grid or not self.moving:return []
  ps=programs(raw['frame'],self.grid);excluded=[self.grid['box']]+[p['panel']for p in ps];inks={c['ink']for c in cues(raw,self.grid)}-getattr(self,'ranged_excluded_inks',set())
  return[o for o in objects(raw['frame'],excluded)if not o.get('parts')and o['ink']in inks and gap(o['box'],self.grid['box'])>12]
