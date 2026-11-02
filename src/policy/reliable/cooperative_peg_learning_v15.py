"""Retrieve the earlier observed movable-pivot skill after a planning impasse."""
import copy
from cooperative_peg_learning_v13 import Agent as Prefix
from cooperative_peg_bridge_core_v2 import Agent as Revised
class Agent(Prefix):
 def __init__(self,prior=None):super().__init__(prior);self.bridge_mode=False
 def respond(self,raw):
  if self.bridge_mode:return Revised.respond(self,raw)
  result=super().respond(raw)
  if not result['done']or(result.get('certificate')or{}).get('reason')!='no_typed_jump_plan':return result
  memory=self.prefix.prefix.core.memory
  if not memory.movable_pivot_rules:return result
  self.rule.update(movable_pivot_rules=copy.deepcopy(memory.movable_pivot_rules),permanent_rules=copy.deepcopy(memory.permanent_rules),movable_transfer_source=self.t)
  self.region_mode=None;self.bridge_mode=True
  return Revised.respond(self,raw)
