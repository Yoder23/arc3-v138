import copy,hashlib,json
from rare_actor_jump_inquiry_v1 import Agent as Prefix
from paired_carrier_geometry_v2 import scene,positions
from cooperative_peg_model_v2 import search
from cooperative_peg_joint_model_v3 import search as joint_search
from cooperative_peg_region_goals_v1 import propose as region_goals

from cooperative_peg_perception_v6 import view,rail_trial,enrich
from cooperative_peg_registration_v5 import infer
class Agent:
 def __init__(self,prior=None):self.prior=prior;self.active=True;self.prefix=Prefix();self.own=False;self.t=0;self.rule=None;self.carrier_ink=None;self.selected=None;self.previous=None;self.outcomes=[];self.failures=[];self.archives=[];self.level=None;self.stopped=False;self.transfer_moves=0;self.goal_refutations=[];self.camera_events=[];self.rail_direction=None;self.rail_attempts=[];self.permanent_rules=[];self.track=None;self.track_evidence=[];self.region_mode=None
 def respond(self,raw):
  if not self.own:
   r=self.prefix.respond(raw)
   if not r['done']:self.t+=1;return r
   if not self.prefix.trial or len(self.prefix.outcomes)!=2:return r
   p=self.prefix.trial;o=self.prefix.outcomes[-1];a,b,z=p['jump'];k=(p['scene']['size']-1)//2;f=o['after']['frame'];before=o['before']['frame']
   if f[a[0]+k][a[1]+k]!=p['scene']['field']or f[z[0]+k][z[1]+k]!=p['actor_ink']or before[b[0]+k][b[1]+k]!=f[b[0]+k][b[1]+k]:return r
   self.rule=dict(source=o['source'],selection_source=p['source'],ordinary_ink=p['scene']['mark'],helper_ink=p['actor_ink'],size=p['scene']['size'],field=p['scene']['field'],pitch=p['scene']['pitch'],jump=p['jump'],preserves_intermediate=True,hypothesis='compose_observed_helper_jump_with_a_reciprocal_ordinary_jump_test')
   self.carrier_ink=self.prefix.prefix.core.memory.template['body']['ink'];self.rule['carrier_ink']=self.carrier_ink;self.permanent_rules=copy.deepcopy(self.prefix.prefix.core.memory.permanent_rules);self.track=None;self.own=True;self.level=raw['levels_completed']
  if self.previous:
   old=self.previous;after=view(raw,self.rule,self.carrier_ink);r=dict(source=old['source'],action=old['action'],data=old['data'],before=old['before'],after=copy.deepcopy(raw),prediction=old['prediction'],view_after=after)
   if not old['prediction'] and old['action']in(1,2,3,4)and raw['levels_completed']==self.level:
    r['registration']=infer(old['before']['frame'],raw['frame'],self.rule)
    if r['registration']['supported']:self.camera_events.append(dict(source=old['source'],registration=copy.deepcopy(r['registration'])))
    if old.get('transfer'):
     delta=r['registration']['delta'];expected=sorted(tuple(p[j]-delta[j]for j in(0,1))for p in old['transfer']['positions_predicted']);r['carrier_prediction_matched']=after is not None and sorted(after['carrier_positions'])==expected
     if not r['carrier_prediction_matched']:self.failures.append(dict(source=old['source'],reason='conditional_carrier_motion_prediction_refuted',expected=expected,observed=after['carrier_positions']if after else None))
     if r['carrier_prediction_matched']and old['transfer']['rail_support']:
      colors={p['ink']for p in old['transfer']['rail_support']}
      if len(colors)==1:
       ink=next(iter(colors))
       if self.track is None:self.track=ink;self.track_evidence.append(dict(source=old['source'],ink=ink,rail_support=copy.deepcopy(old['transfer']['rail_support']),registration=copy.deepcopy(r['registration']),observed_positions=after['carrier_positions']))
   if old['prediction']and raw['levels_completed']==self.level:
    q=old['prediction'];registration=infer(old['before']['frame'],raw['frame'],self.rule);r['registration']=registration;delta=registration['delta'];n=self.rule['size']
    if registration['supported']:self.camera_events.append(dict(source=old['source'],registration=copy.deepcopy(registration)))
    def matches(expected,actual):
     transformed={tuple(p[j]-delta[j]for j in(0,1))for p in expected};visible={p for p in transformed if all(0<=p[j]<=64-n for j in(0,1))};extra=set(actual)-visible
     return visible<=set(actual)and all(any(p[j]+delta[j]<0 or p[j]+delta[j]>64-n for j in(0,1))for p in extra)
    r['matched']=after is not None and matches(q['ordinary_after'],after['ordinary'])and matches(q['helpers_after'],after['helpers'])
    if not r['matched']:self.failures.append(r);self.stopped=True
   self.outcomes.append(r);self.previous=None
  if raw['levels_completed']!=self.level:
   self.archives.append(dict(level=self.level,rule=copy.deepcopy(self.rule),outcome_sources=[v['source']for v in self.outcomes]));self.level=raw['levels_completed'];self.selected=None;self.region_mode=None
  if self.stopped or raw['state']!='NOT_FINISHED'or self.t>=640:return dict(done=True,action=None,data={},certificate=dict(cooperative_rule=self.rule,outcomes=self.outcomes,failures=self.failures,archives=self.archives))
  v=view(raw,self.rule,self.carrier_ink)
  if not v:return dict(done=True,action=None,data={},certificate=dict(cooperative_rule=self.rule,reason='scene_outside_observed_representation'))
  v=enrich(raw,v,self.permanent_rules,self.track)
  frame_key=hashlib.sha256(json.dumps(raw['frame'][1:],separators=(',',':')).encode()).hexdigest();excluded=[p['action']for p in self.rail_attempts if p['frame_key']==frame_key]
  prediction=None;plan=None;stats={};goal_carriers=None;transfer=None;planned_move=None;joint=False;joint_target=1;joint_goal_mode='reduce';frontiers=[];region_proposal=None;action=6;n=v['scene']['size'];k=(n-1)//2
  if self.selected:
   old=self.selected;self.selected=None;prediction=old['step'];z=prediction['jump'][2];before=old['before']['frame'];f=raw['frame']
   if not any(before[y][x]!=f[y][x]for y in range(z[0],z[0]+n)for x in range(z[1],z[1]+n)):
    self.failures.append(dict(source=old['source'],reason='proposed_landing_not_highlighted'));self.stopped=True;return dict(done=True,action=None,data={},certificate=dict(cooperative_rule=self.rule,failures=self.failures))
   target=z;tag='test_composed_typed_jump_landing'
  else:
   if self.region_mode==self.level:
    region_proposal=region_goals(raw,v,self.outcomes,self.rule,self.carrier_ink);frontiers=region_proposal['goals'];joint_goal_mode='frontier'
    if frontiers:plan,stats=joint_search(v['scene']['cells'],v['rails'],v['carrier_positions'],v['ordinary'],v['helpers'],v['pivots'],v['scene']['pitch'],goal_mode=joint_goal_mode,frontiers=frontiers);joint=bool(plan)
    if not plan:self.region_mode=None
   if not plan:
    plan,stats=joint_search(v['scene']['cells'],v['rails'],v['carrier_positions'],v['ordinary'],v['helpers'],v['pivots'],v['scene']['pitch']);joint=bool(plan)
    if plan is None and len(v['ordinary'])>2:
     joint_target=len(v['ordinary'])-1;plan,stats=joint_search(v['scene']['cells'],v['rails'],v['carrier_positions'],v['ordinary'],v['helpers'],v['pivots'],v['scene']['pitch'],target_count=joint_target);joint=bool(plan)
    if not plan and len(v['ordinary'])<=1 and v['helpers'] and v['carrier_positions']:
     if not self.goal_refutations:self.goal_refutations.append(dict(source=self.t,level=self.level,ordinary=v['ordinary'],helpers=v['helpers'],state=raw['state'],refuted='one_visible_ordinary_token_suffices_for_level_completion'))
     goal_carriers=v['carrier_positions'];joint_goal_mode='load';plan,stats=joint_search(v['scene']['cells'],v['rails'],v['carrier_positions'],v['ordinary'],v['helpers'],v['pivots'],v['scene']['pitch'],goal_mode=joint_goal_mode);joint=bool(plan)
     if plan==[] and self.transfer_moves<56:
      transfer=rail_trial(raw,v,self.prefix.prefix.core.controls,self.rail_direction,excluded)
      if transfer:self.transfer_moves+=1;action=transfer['action'];tag='move_loaded_helper_carriers';self.rail_direction=transfer['delta']
    if not plan and transfer is None and v['helpers']:
     pitch=v['scene']['pitch'];cells=set(map(tuple,v['scene']['cells']));edges={p for p in cells if any(p[j]-pitch<0 or p[j]+pitch+n>64 for j in(0,1))};frontiers=sorted(edges|{p for p in cells if any(abs(p[0]-q[0])+abs(p[1]-q[1])==pitch for q in edges)})
     if frontiers and not set(v['ordinary'])&set(frontiers):
      joint_goal_mode='frontier';plan,stats=joint_search(v['scene']['cells'],v['rails'],v['carrier_positions'],v['ordinary'],v['helpers'],v['pivots'],v['scene']['pitch'],goal_mode=joint_goal_mode,frontiers=frontiers);joint=bool(plan)
    if not plan and transfer is None and v['helpers'] and set(v['helpers'])<=set(v['carrier_positions'])and set(v['ordinary'])&set(v['carrier_positions'])and self.transfer_moves<56:
     transfer=rail_trial(raw,v,self.prefix.prefix.core.controls,self.rail_direction,excluded)
     if transfer:self.transfer_moves+=1;action=transfer['action'];tag='move_loaded_helper_carriers';self.rail_direction=transfer['delta']
    if not plan and transfer is None:
     region_proposal=region_goals(raw,v,self.outcomes,self.rule,self.carrier_ink);frontiers=region_proposal['goals'];joint_goal_mode='frontier'
     if frontiers:plan,stats=joint_search(v['scene']['cells'],v['rails'],v['carrier_positions'],v['ordinary'],v['helpers'],v['pivots'],v['scene']['pitch'],goal_mode=joint_goal_mode,frontiers=frontiers);joint=bool(plan)
     if plan:self.region_mode=self.level
    if not plan and transfer is None:return dict(done=True,action=None,data={},certificate=dict(cooperative_rule=self.rule,view=v,search=stats,reason='no_typed_jump_plan',region_proposal=region_proposal,outcomes=self.outcomes,archives=self.archives,goal_refutations=self.goal_refutations))
   if plan:
    if plan[0].get('kind')=='move':
     planned_move=plan[0];prediction=planned_move;action=self.prefix.prefix.core.controls[tuple(planned_move['delta'])];tag='move_carriers_for_cooperative_plan'
    else:target=plan[0]['jump'][0];tag='select_composed_typed_jump';self.selected=dict(step=plan[0],source=self.t,before=copy.deepcopy(raw))
  attempts_before=copy.deepcopy(self.rail_attempts)
  if transfer:self.rail_attempts.append(dict(source=self.t,level=self.level,frame_key=frame_key,action=action))
  data={}if transfer or planned_move else dict(x=target[1]+k,y=target[0]+k);c=dict(kind='cooperative_peg_learning',source=self.t,tag=tag,rule=copy.deepcopy(self.rule),view=v,goal_carriers=goal_carriers,transfer=transfer,planned_move=planned_move,joint_plan=joint,joint_target=joint_target,joint_goal_mode=joint_goal_mode,frontiers=frontiers,region_proposal=region_proposal,region_mode=self.region_mode,rail_attempts=attempts_before,excluded_actions=excluded,frame_key=frame_key,rail_direction=self.rail_direction,controls=[dict(delta=d,action=a)for d,a in sorted(self.prefix.prefix.core.controls.items())],goal_refutations=copy.deepcopy(self.goal_refutations),carrier_ink=self.carrier_ink,track_evidence=copy.deepcopy(self.track_evidence),plan=plan,prediction=prediction,search=stats,outcomes=copy.deepcopy(self.outcomes),archives=copy.deepcopy(self.archives),camera_events=copy.deepcopy(self.camera_events),goal_is_hypothesis=True)
  self.previous=dict(source=self.t,action=action,data=data,before=copy.deepcopy(raw),prediction=prediction,transfer=transfer);self.t+=1
  return dict(done=False,action=action,data=data,certificate=c)
