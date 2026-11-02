"""Verify selection against an observed active marker; retain successful click offsets."""
import copy
from selectable_multi_object_learner_v14 import Agent as Base
class Agent(Base):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.marker_witness=None;self.selection_observations=[];self.selection_skills=[];self.selection_failures=set()
    def reset_level(self,raw):
        super().reset_level(raw);self.marker_witness=None;self.selection_failures=set()
    def observe(self,raw):
        old=self.previous;old_active=self.active_box;push_count=len(self.push_memory);result=super().observe(raw)
        if not result or not old or old['raw']['levels_completed']!=raw['levels_completed']:return result
        if len(self.push_memory)>push_count:
            q=next((q for q in self.objects if tuple(q['box'])==tuple(self.active_box or ())),None)
            if q:self.active_center=q['center']
        elif old['action'] in self.motions:
            m=self.motions[old['action']]
            if m['source']==old['source'] and tuple(m['after']['box'])==tuple(self.active_box or ()):
                self.marker_witness=dict(source=old['source'],action=old['action'],motion=copy.deepcopy(m),ink=m['after']['center']);self.active_center=m['after']['center']
        target=old.get('target')
        if old['action']==6 and target:
            y,x,h,w=target['box'];q=next((q for q in self.objects if tuple(q['box'])==tuple(target['box'])),None);after=raw['frame'][y+h//2][x+w//2];marker=self.marker_witness['ink'] if self.marker_witness else None
            changed=target['center']!=after;accepted=bool(q and marker is not None and after==marker);offset=(old['data']['x']-x,old['data']['y']-y);ident=self.identities.get(tuple(target['box']))
            record=dict(source=old['source'],target=copy.deepcopy(target),after_target=copy.deepcopy(q),after_center=after,point=copy.deepcopy(old['data']),marker=copy.deepcopy(self.marker_witness),accepted=accepted,changed=changed,outcome='observed_active_marker' if accepted else 'target_not_observed_active')
            self.selection_observations.append(record)
            if accepted:
                self.active_box=tuple(q['box'])
                if changed and not any(tuple(s['shape'])==(h,w) and tuple(s['offset'])==offset for s in self.selection_skills):
                    self.selection_skills.append(dict(source=old['source'],shape=(h,w),offset=offset,marker=copy.deepcopy(self.marker_witness),hypothesis='successful_visible_click_offset_may_transfer_to_similar_body'))
            else:
                self.selection_failures.add((self.level,ident,(h,w),offset,target['center']))
                active=[q for q in self.objects if marker is not None and q['center']==marker]
                self.active_box=tuple(active[0]['box']) if len(active)==1 else old_active
        return result
    def answer(self,raw,a,d,tag,target=None,route=None,goal=None):
        point_hypothesis=None
        if a==6 and target and 'select' in tag:
            y,x,h,w=target['box'];ident=self.identities.get(tuple(target['box']));candidates=[]
            for skill in self.selection_skills:
                if tuple(skill['shape'])==(h,w):candidates.append((tuple(skill['offset']),skill['source']))
            candidates.append(((w//2,h//2),None))
            candidates.extend((offset,None) for offset in [(1,1),(w-2,1),(1,h-2),(w-2,h-2)])
            seen=set();available=[]
            for offset,source in candidates:
                if offset in seen or not(0<=offset[0]<w and 0<=offset[1]<h):continue
                seen.add(offset)
                if (self.level,ident,(h,w),offset,target['center']) not in self.selection_failures:available.append((offset,source))
            if not available:return dict(done=True,action=None,data={})
            offset,source=available[0];d=dict(x=x+offset[0],y=y+offset[1]);point_hypothesis=dict(offset=offset,retained_source=source,hypothesis='test_visible_point_for_object_selection')
        result=super().answer(raw,a,d,tag,target,route,goal)
        if not result['done']:
            result['certificate'].update(selection_observations=copy.deepcopy(self.selection_observations),selection_skills=copy.deepcopy(self.selection_skills),selection_point_hypothesis=point_hypothesis)
        return result
