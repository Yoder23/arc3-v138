import copy
from elastic_goal_inquiry_v3 import Agent as Prior
from rectangle_transfer_scene_v2 import scene,digest
from rectangle_transfer_model_v1 import selected,assignment,observe,plan,covered
class Agent:
 def __init__(self):self.prior=Prior();self.active=False;self.last=None;self.pending=None;self.history=[];self.failed=[];self.sequences={};self.steps=0
 def stop(self,reason,**kwargs):return dict(action=None,data={},done=True,certificate=None,advisor='rectangle_transfer_inquiry',diagnostics=dict(reason=reason,steps=self.steps,**kwargs))
 def respond(self,o):
  if not self.active:
   r=self.prior.respond(o)
   if not r['done']:
    self.last=(copy.deepcopy(o),copy.deepcopy(r));return r
   if r['diagnostics'].get('reason')!='new_level_preserve_composed_knowledge':return r
   sc=scene(o)
   if sc is None:return self.stop('new_scene_requires_other_representation')
   before,last=self.last;self.transfer_source=digest(dict(before=before,action=last['action'],data=last['data'],after=o));self.initial=sc;self.figures=copy.deepcopy(sc['figures']);self.models=self.prior.models;self.mechanism=self.prior.mechanism;self.retained_trials=copy.deepcopy(self.prior.trials);self.retained_candidates=self.prior.candidates[:];self.selected=selected(self.figures,o['frame']);self.binding=assignment(self.figures,sc);self.level=o['levels_completed'];self.active=True
  if o['levels_completed']!=self.level or o['state']!='NOT_FINISHED':return self.stop('terminal_or_new_level')
  if self.pending:
   before,action,figures,active=self.pending;result=observe(figures,active,o['frame'],action,self.initial,self.models,self.mechanism)
   if result is None:return self.stop('unresolved_transferred_rectangle_observation')
   self.figures,self.selected,outcome=result;source=digest(dict(before=before,action=action,data={},after=o));self.history.append(dict(source=source,outcome=outcome))
   if outcome['kind']=='alternative':self.failed.append(dict(source=source,figure=active,state=figures[active]['state'],color=figures[active]['color'],action=action));self.sequences={}
   self.pending=None
  if self.binding is None:return self.stop('invariant_cannot_assign_goals')
  if self.steps>=200:return self.stop('bounded_transfer_trial')
  path=None;stats={};reason='transfer_and_compose_rectangle_rule'
  if self.selected is None or covered(self.figures[self.selected],self.binding[self.selected],self.initial):action=5;reason='select_unfinished_rectangle'
  else:
   i=self.selected
   if not self.sequences.get(i):self.sequences[i],stats=plan(self.figures,i,self.binding[i],self.initial,self.models,self.mechanism,{(tuple(q['state']),q['color'],q['action']) for q in self.failed if q['figure']==i})
   if not self.sequences.get(i):return self.stop('no_transfer_plan',search=stats,binding=self.binding,active=i)
   path=self.sequences[i][:];action=path[0];self.sequences[i].pop(0)
  c=dict(kind='rectangle_rule_transfer',context=digest(o),transfer_source=self.transfer_source,initial=self.initial,figures=copy.deepcopy(self.figures),active=self.selected,binding=self.binding,models=self.models,mechanism=self.mechanism,retained_trials=self.retained_trials,retained_candidates=self.retained_candidates,history=copy.deepcopy(self.history),failed=copy.deepcopy(self.failed),path=path,goal_is_hypothesis=True,transfer_is_hypothesis=True)
  self.pending=(copy.deepcopy(o),action,copy.deepcopy(self.figures),self.selected);self.steps+=1
  return dict(action=action,data={},done=False,certificate=c,advisor='rectangle_transfer_inquiry',diagnostics=dict(reason=reason,steps=self.steps,binding=self.binding,active=self.selected,search=stats))
