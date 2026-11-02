import copy
from component_figure_inquiry_v2 import Agent as Prior
from rectangle_observation_v1 import bounds
from rectangle_contact_model_v2 import advance as rect_advance
from elastic_figure_model_v3 import assignment,covered,observe,plan,selected
from visual_transform_learner import digest
from visible_goal_memory_v1 import visible,merge,scene as goal_scene
class Agent:
 def __init__(self):self.prior=Prior();self.active=False;self.pending=None;self.history=[];self.trials=[];self.failed=[];self.sequences={};self.steps=0;self.candidates=['turn_ccw','turn_cw','contact','centered'];self.archived=[]
 def stop(self,reason):return dict(action=None,data={},done=True,certificate=None,advisor='elastic_goal_inquiry',diagnostics=dict(reason=reason,steps=self.steps,candidate_models=self.candidates,retained_rect_trials=len(self.trials)))
 def respond(self,o):
  if self.active and self.level!=o['levels_completed']:
   self.archived.append(dict(initial=self.initial,models=self.models,trials=self.trials,history=self.history,figures=self.figures));return self.stop('new_level_preserve_composed_knowledge')
  if not self.active:
   r=self.prior.respond(o)
   if not r['done'] or r['diagnostics'].get('reason')!='ambiguous_component_transition_requires_new_observation_model' or not self.prior.pending:return r
   before,action,figures,active=self.prior.pending
   if active is None or figures[active]['kind']!='rectangle':return r
   self.initial=self.prior.initial;self.models=self.prior.models;self.rect=active;self.selected=active;self.figures=copy.deepcopy(figures);self.level=o['levels_completed'];f=figures[active];old=bounds(before['frame'],f['color'],self.initial);new=bounds(o['frame'],f['color'],self.initial)
   if old is None or new is None:return r
   source=digest(dict(before=before,action=action,data={},after=o));self.activation_source=source;self.figures[active]=dict(f,kind='elastic_rectangle',state=new,perimeter=old[2]-old[0]+old[3]-old[1]);self.trials=[dict(source=source,action=action,before=old,after=new,before_color=f['color'],after_color=f['color'])];self.active=True;self.binding=None;self.mechanism='centered';self.goal_observations=[];self.targets=copy.deepcopy(self.initial['targets'])
  if self.pending:
   before,action,figures,active,mechanism=self.pending;source=digest(dict(before=before,action=action,data={},after=o));updated=merge(self.targets,visible(o['frame']));
   if updated!=self.targets:self.goal_observations.append(dict(source=source,targets=visible(o['frame'])));self.targets=updated;self.binding=None;self.sequences={}
   result=observe(figures,self.rect,goal_scene(self.initial,self.targets),o['frame'],action,self.models,active,mechanism)
   if result is None:return self.stop('unresolved_elastic_observation')
   self.figures,self.selected,outcome=result;self.history.append(dict(source=source,outcome=outcome))
   if action!=5 and active==self.rect:self.trials.append(dict(source=source,action=action,before=figures[active]['state'],after=self.figures[active]['state'],before_color=figures[active]['color'],after_color=self.figures[active]['color']))
   if outcome['kind']=='alternative':self.failed.append(dict(source=source,figure=active,state=figures[active]['state'],color=figures[active]['color'],action=action,model=mechanism));self.sequences={}
   self.pending=None
  sc=goal_scene(self.initial,self.targets);site=set(map(tuple,self.initial['site']['points']));self.candidates=[m for m in self.candidates if all(list(rect_advance(t['before'],self.models[t['action']]['delta'],site,m))==t['after'] for t in self.trials)]
  if not self.candidates:return self.stop('all_rectangle_hypotheses_refuted')
  self.mechanism='centered' if 'centered' in self.candidates else self.candidates[0]
  if o['state']!='NOT_FINISHED':return self.stop('terminal')
  if self.steps>=180:return self.stop('bounded_elastic_inquiry')
  action=None;path=None;stats={};reason='compose_revised_shape_color_goal'
  if len(self.candidates)>1 and len(self.trials)<4 and self.selected==self.rect:
   q=self.figures[self.rect]['state'];options=[(len({rect_advance(q,m['delta'],site,c) for c in self.candidates}),a) for a,m in self.models.items()];gain,trial=max(options)
   if gain>1:action=trial;reason='discriminate_rectangle_contact_models'
  if self.binding is None:self.binding=assignment(self.figures,self.rect,sc)
  if self.binding is None:return self.stop('no_goal_assignment_consistent_with_observed_perimeter')
  if action is None:
   occupied=[i for i,f in enumerate(self.figures) if i!=self.rect and f['color']==self.binding[self.rect] and f['color']!=self.binding[i]]
   if self.selected is None or occupied and self.selected!=occupied[0]:action=5;reason='free_color_identity_before_recoloring_rectangle'
   else:
    i=self.selected;f=self.figures[i]
    if covered(f,self.binding[i],sc,i==self.rect):action=5;reason='select_next_unfinished_goal'
    else:
     if not self.sequences.get(i):self.sequences[i],stats=plan(f,self.binding[i],i==self.rect,sc,self.models,self.mechanism,{(tuple(q['state']),q['color'],q['action']) for q in self.failed if q['figure']==i and q['model']==self.mechanism})
     if not self.sequences.get(i):return self.stop('no_plan_under_surviving_contact_model')
     path=self.sequences[i][:];action=path[0];self.sequences[i].pop(0)
  c=dict(kind='elastic_goal_revision',context=digest(o),activation_source=self.activation_source,initial=self.initial,targets=self.targets,goal_observations=copy.deepcopy(self.goal_observations),figures=copy.deepcopy(self.figures),rect=self.rect,active=self.selected,binding=self.binding,models=self.models,trials=copy.deepcopy(self.trials),candidate_models=self.candidates,mechanism=self.mechanism,history=copy.deepcopy(self.history),failed=copy.deepcopy(self.failed),path=path,goal_is_hypothesis=True,perimeter_is_hypothesis=True,mechanism_is_hypothesis=True);self.pending=(copy.deepcopy(o),action,copy.deepcopy(self.figures),self.selected,self.mechanism);self.steps+=1
  return dict(action=action,data={},done=False,certificate=c,advisor='elastic_goal_inquiry',diagnostics=dict(reason=reason,steps=self.steps,active=self.selected,binding=self.binding,candidates=self.candidates,search=stats))
