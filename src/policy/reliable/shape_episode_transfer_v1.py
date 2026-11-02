"""Reset solved scene plans while retaining measured controls and archived interaction lessons."""
import copy
from articulated_line_planner_v6 import Agent as Prior
class Agent:
 def __init__(self):self.agent=Prior();self.archived=[];self.level=None
 def respond(self,obs):
  if self.level!=obs['levels_completed']:
   old=self.agent
   if old.prior.planning and old.prior.level is not None and obs['levels_completed']>old.prior.level:
    # An inactive controller must not attribute another controller's last action to itself.
    controller=copy.deepcopy(old.prior.prior.prior)
    controller.prior.previous=None;controller.prior.last=None;controller.prior.pending=None
    if controller.shared is not None:controller.shared.previous=None;controller.shared.last=None;controller.shared.track.previous=None
    self.archived.append(old);self.agent=Prior();self.agent.prior.prior.prior=controller
   self.level=obs['levels_completed']
  return self.agent.respond(obs)
