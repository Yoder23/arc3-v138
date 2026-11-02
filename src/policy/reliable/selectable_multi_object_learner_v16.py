"""Resolve a changed but unclassified selection with a bounded motor experiment."""
import copy
from selectable_multi_object_learner_v15 import Agent as Base
class Agent(Base):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.selection_bootstrap=None
    def reset_level(self,raw):
        super().reset_level(raw);self.selection_bootstrap=None
    def observe(self,raw):
        old=self.previous;pending=copy.deepcopy(self.selection_bootstrap);result=super().observe(raw)
        if not result or not old or old['raw']['levels_completed']!=raw['levels_completed']:return result
        if pending and old['action'] in (1,2,3,4):
            m=self.motions.get(old['action'])
            if m and m['source']==old['source'] and tuple(m['before']['box'])==tuple(pending['box']) and self.marker_witness and self.marker_witness['source']==old['source']:
                record=next(r for r in self.selection_observations if r['source']==pending['source'])
                record.update(marker=copy.deepcopy(self.marker_witness),accepted=True,outcome='target_control_confirmed_by_subsequent_motion',confirmation_source=old['source'])
                y,x,h,w=record['target']['box'];offset=(record['point']['x']-x,record['point']['y']-y)
                if not any(tuple(s['shape'])==(h,w) and tuple(s['offset'])==offset for s in self.selection_skills):self.selection_skills.append(dict(source=record['source'],shape=(h,w),offset=offset,marker=copy.deepcopy(self.marker_witness),hypothesis='successful_visible_click_offset_may_transfer_to_similar_body'))
                self.selection_bootstrap=None
            else:
                self.selection_bootstrap['tested'].append(old['action'])
                if len(self.selection_bootstrap['tested'])>=4:self.selection_bootstrap=None
        if old['action']==6 and self.selection_observations and self.selection_observations[-1]['source']==old['source']:
            record=self.selection_observations[-1]
            if record['changed'] and record['marker'] is None and record['after_target']:
                self.selection_bootstrap=dict(source=old['source'],box=tuple(record['target']['box']),tested=[])
                self.active_box=tuple(record['target']['box'])
        return result
    def answer(self,raw,a,d,tag,target=None,route=None,goal=None):
        if self.selection_bootstrap:
            choices=[v for v in (1,2,3,4) if v in raw['available_actions'] and v not in self.selection_bootstrap['tested']]
            if choices:a=choices[0];d={};tag='test_changed_selection_by_motion';target=None;route=None;goal=None
        r=super().answer(raw,a,d,tag,target,route,goal)
        if not r['done']:r['certificate']['selection_bootstrap']=copy.deepcopy(self.selection_bootstrap)
        return r
