"""Learn delayed pushes from actual other-body motion; retain conditional failures."""
import copy,heapq,itertools
from collections import Counter
from selectable_rect_inquiry_v2 import Agent as Base
from selectable_multi_object_learner_v2 import inside

def overlap(a,b):return a[0]<b[0]+b[2] and b[0]<a[0]+a[2] and a[1]<b[1]+b[3] and b[1]<a[1]+a[3]
class Agent(Base):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.push_memory=[];self.push_constraints=[];self.contact_inquiries=set();self.disable_push=False
    def reset_level(self,raw):
        super().reset_level(raw);self.push_constraints=[];self.contact_inquiries=set()
    def observe(self,raw):
        old=self.previous;active=self.active_box;old_ids=dict(self.identities);before=copy.deepcopy(self.objects);old_motions=copy.deepcopy(self.motions)
        result=super().observe(raw)
        if not result or not old or old['action'] not in old_motions or old['raw']['levels_completed']!=raw['levels_completed'] or active is None:return result
        actor=next((o for o in before if tuple(o['box'])==tuple(active)),None)
        if not actor:return result
        delta=tuple(old_motions[old['action']]['delta']);dest=tuple(actor['box'][i]+delta[i] for i in (0,1));other=next((o for o in before if o is not actor and overlap((*dest,*actor['box'][2:]),o['box'])),None)
        if not other:return result
        same_actor=next((o for o in self.objects if tuple(o['box'])==tuple(actor['box'])),None)
        pushed_pos=tuple(other['box'][i]+delta[i] for i in (0,1));moved=next((o for o in self.objects if tuple(o['box'][:2])==pushed_pos),None)
        if same_actor and moved:
            self.push_memory.append(dict(source=old['source'],action=old['action'],actor=actor,object=other,after=moved,delta=delta,outcome='observed_other_body_translation_while_actor_stays'))
            self.active_box=tuple(active);self.motions[old['action']]=old_motions[old['action']]
        elif same_actor and any(tuple(o['box'])==tuple(other['box']) for o in self.objects):
            y,x=pushed_pos;h,w=other['box'][2:]
            if 0<=y<=64-h and 0<=x<=64-w:
                self.push_constraints.append(dict(source=old['source'],identity=old_ids[tuple(other['box'])],actor=actor,object=other,delta=delta,destination=pushed_pos,pattern=tuple(old['raw']['frame'][yy][xx] for yy in range(y,y+h) for xx in range(x,x+w)),hypothesis='observed_push_context_did_not_displace_either_body',causality_confirmed=False))
        return result
    def answer(self,raw,a,d,tag,target=None,route=None,goal=None):
        if not self.disable_push and not self.push_memory:
            actor=next((q for q in self.objects if tuple(q['box'])==tuple(self.active_box or ())),None)
            if actor:
                for other in self.objects:
                    if other is actor:continue
                    for action,m in self.motions.items():
                        dest=tuple(actor['box'][i]+m['delta'][i] for i in (0,1));key=(self.level,tuple(actor['box']),tuple(other['box']),action)
                        if overlap((*dest,*actor['box'][2:]),other['box']) and key not in self.contact_inquiries:
                            self.contact_inquiries.add(key);a=action;d={};tag='test_body_contact_model';target=None;route=None;goal=None;break
                    else:continue
                    break
        result=super().answer(raw,a,d,tag,target,route,goal)
        result['certificate']['push_memory']=copy.deepcopy(self.push_memory);result['certificate']['push_constraints']=copy.deepcopy(self.push_constraints)
        return result
