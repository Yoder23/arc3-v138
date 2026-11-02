import copy
from shape_episode_transfer_v1 import Agent as Prior
from component_figure_scene_v2 import scene
from component_figure_model_v4 import assignment,plan,observe,selected,pixels
from visual_transform_learner import digest
class Agent:
 def __init__(self):self.prior=Prior();self.initial=None;self.level=None;self.models={};self.figures=[];self.binding=None;self.active=None;self.pending=None;self.history=[];self.steps=0;self.sequences={};self.refutations=[];self.archived=[];self.failed=[]
 def stop(self,reason):return dict(action=None,data={},done=True,certificate=None,advisor='component_figure_inquiry',diagnostics=dict(reason=reason,steps=self.steps,refutations=len(self.refutations)))
 def respond(self,o):
  if self.level!=o['levels_completed']:
   if self.initial:self.archived.append(dict(initial=self.initial,models=self.models,history=self.history,refutations=self.refutations))
   self.level=o['levels_completed'];self.initial=None;self.pending=None;self.figures=[];self.sequences={};self.history=[];self.refutations=[];self.steps=0;self.failed=[]
  if self.initial is None:
   sc=scene(o)
   if not sc:return self.prior.respond(o)
   controller=self.prior.agent.prior.prior.prior;source=controller.shared or controller.prior;self.models=copy.deepcopy({a:m for a,m in source.models.items() if len({tuple(q['origin']) for q in m['support']})>=2})
   if len(self.models)!=4:return self.stop('missing_measured_motion_controls')
   self.initial=copy.deepcopy(sc);self.initial_source=digest(o);self.figures=copy.deepcopy(sc['figures']);self.binding=list(assignment(sc,self.models) or []);self.active=selected(self.figures,o['frame'])
   if len(self.binding)!=len(self.figures):return self.stop('no_complete_shape_color_assignment')
  if self.pending:
   before,action,prior,active=self.pending;source=digest(dict(before=before,action=action,data={},after=o));result=observe(prior,self.initial,o['frame'],action,self.models,active)
   if result is None:return self.stop('ambiguous_component_transition_requires_new_observation_model')
   self.figures,self.active,outcome=result;self.history.append(dict(source=source,outcome=outcome))
   if outcome['kind']=='alternative':
    self.refutations.append(dict(source=source,outcome=outcome));self.sequences={};f=prior[outcome['figure']];self.failed.append(dict(source=source,figure=outcome['figure'],state=f['state'],color=f['color'],action=action))
   self.pending=None
  if o['state']!='NOT_FINISHED':return self.stop('terminal')
  if self.steps>=180:return self.stop('bounded_component_inquiry')
  action=5;path=None;stats={};target=None
  if self.active is not None:
   i=self.active;fig=self.figures[i];target=self.binding[i];covered=fig['color']==target and set(map(tuple,self.initial['targets'][target]))<=set.union(*pixels(fig['state'],fig['segments']))
   if not covered:
    if not self.sequences.get(i):self.sequences[i],stats=plan(fig,target,self.initial,self.models,limit=150000,blocked={(tuple(q['state']),q['color'],q['action']) for q in self.failed if q['figure']==i})
    if not self.sequences.get(i):return self.stop('no_reachable_goal_under_current_mechanism')
    path=self.sequences[i][:];action=path[0];self.sequences[i].pop(0)
  c=dict(kind='component_figure_composition',context=digest(o),initial=self.initial,initial_source=self.initial_source,figures=copy.deepcopy(self.figures),active=self.active,binding=self.binding,models=copy.deepcopy(self.models),history=copy.deepcopy(self.history),refutations=copy.deepcopy(self.refutations),failed=copy.deepcopy(self.failed),path=path,target=target,goal_is_hypothesis=True,mechanism_is_hypothesis=True,clipping_is_hypothesis=True,paint_extent_is_hypothesis=True);self.pending=(copy.deepcopy(o),action,copy.deepcopy(self.figures),self.active);self.steps+=1
  return dict(action=action,data={},done=False,certificate=c,advisor='component_figure_inquiry',diagnostics=dict(reason='test_joint_shape_color_goal_and_replan_after_refutation',steps=self.steps,active=self.active,target=target,refutations=len(self.refutations),search=stats))
