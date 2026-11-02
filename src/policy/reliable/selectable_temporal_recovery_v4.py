"""Preserve reliable controls after unexpected transitions and retire contradicted constraints."""
import copy
from selectable_fragmentary_goal_v2 import Agent as Base
class Agent(Base):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.control_exceptions=[];self.refuted_motion_constraints=[];self.recovery_wait=0;self.control_level_start=0
    def reset_level(self,raw):
        super().reset_level(raw);self.control_level_start=self.t
    def observe(self,raw):
        old=self.previous;previous_motions=copy.deepcopy(self.motions);r=super().observe(raw)
        if not old or old['raw']['levels_completed']!=raw['levels_completed'] or not r or len(old['objects'])!=1 or len(self.objects)!=1:return r
        a=old['action'];motion=self.motions.get(a);prior=previous_motions.get(a)
        if not motion or motion['source']!=old['source']:return r
        if prior and tuple(prior['delta'])!=tuple(motion['delta']):
            support=[m for m in self.motion_memory if self.control_level_start<=m['source']<old['source'] and m['action']==a and tuple(m['delta'])==tuple(prior['delta'])]
            if len({m['source'] for m in support})>=3:
                self.control_exceptions.append(dict(source=old['source'],expected=prior,actual=copy.deepcopy(motion),support_sources=sorted({m['source'] for m in support}),cause_unconfirmed=True));self.motions[a]=prior;self.motion_memory=[m for m in self.motion_memory if m['source']!=old['source']];self.recovery_wait=1;return r
        body=motion['before'];dest=tuple(motion['after']['box'][:2]);context=self.context(old['raw'],dest,old['objects'],body)
        retired=[f for f in self.failures if f['source']<old['source'] and f['action']==a and tuple(f['body']['box'])==tuple(body['box']) and tuple(f['destination'])==dest and f['context']==context]
        for f in retired:self.refuted_motion_constraints.append(dict(source=old['source'],failure=copy.deepcopy(f),success=copy.deepcopy(motion),context=context,interpretation='same_local_context_had_a_later_success_so_failure_is_not_a_permanent_rule'))
        removed={f['source'] for f in retired};self.failures=[f for f in self.failures if f['source'] not in removed];self.constraint_hypotheses=[c for c in self.constraint_hypotheses if c['source'] not in removed]
        return r
    def respond(self,raw):
        old=self.previous
        if old and self.level==raw['levels_completed'] and raw['state']=='NOT_FINISHED' and len(old['objects'])==1 and old['action'] in self.motions:
            current=self.detect_objects(raw);m=self.motions[old['action']];before=old['objects'][0]
            if len(current)==1 and tuple(current[0]['box'][2:])==tuple(before['box'][2:]):
                delta=tuple(current[0]['box'][i]-before['box'][i] for i in (0,1));support={q['source'] for q in self.motion_memory if self.control_level_start<=q['source']<old['source'] and q['action']==old['action'] and tuple(q['delta'])==tuple(m['delta'])}
                if delta!=(0,0) and delta!=tuple(m['delta']) and len(support)>=3 and 6 in raw['available_actions']:
                    state=self.passive_probe_state
                    if state and not state.get('contact'):
                        q=state['target'];y,x,h,w=q['box'];changes=[(y+a,x+b,q['ink'],raw['frame'][y+a][x+b]) for a,b in q['shape'] if raw['frame'][y+a][x+b]!=q['ink']]
                        if changes:self.target_invalidations.append(dict(source=old['source'],observed_at=self.t,target=copy.deepcopy(q),changes=changes,causality_is_hypothesis=True,outcome='cached_target_refuted_by_current_pixels'))
                    self.passive_probe_state=None;self.observe(raw);self.recovery_wait=0;body=self.objects[0];y,x,h,w=body['box']
                    return self.answer(raw,6,dict(x=x+w//2,y=y+h//2),'select_active_body_after_unexpected_transition',body,[])
        return super().respond(raw)
    def answer(self,raw,a,d,tag,target=None,route=None,goal=None):
        self.recovery_wait=0
        r=super().answer(raw,a,d,tag,target,route,goal)
        if not r['done']:
            if self.control_exceptions:r['certificate']['control_exceptions']=copy.deepcopy(self.control_exceptions)
            if self.refuted_motion_constraints:r['certificate']['refuted_motion_constraints']=copy.deepcopy(self.refuted_motion_constraints)
        return r
