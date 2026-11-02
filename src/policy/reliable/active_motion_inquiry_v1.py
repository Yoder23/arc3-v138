"""Change experimental conditions after repeated local no-effect probes."""
from collections import Counter
import copy

class InquiryMixin:
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.inquiry_epoch=0;self.inquiry_no_effect={};self.inquiry_visits=Counter()
    def record(self,raw,v):
        old=self.previous
        if old and old['view'] and v and old['raw']['state']==raw['state']=='NOT_FINISHED' and old['raw']['levels_completed']==raw['levels_completed']:
            at=tuple(old['view']['body']['box'][:2]);now=tuple(v['body']['box'][:2])
            self.inquiry_visits[(self.level,self.inquiry_epoch,now)]+=1
            if at==now and old['tag'] in ('motion_inquiry','relocate_motion_inquiry'):
                key=(self.level,self.inquiry_epoch,at,old['action']);self.inquiry_no_effect.setdefault(key,[]).append(old['t'])
        if raw['state']=='GAME_OVER':self.inquiry_epoch+=1
        super().record(raw,v)
    def answer(self,raw,v,action,tag):
        proof=None
        if tag=='motion_inquiry' and v and action not in self.motions:
            at=tuple(v['body']['box'][:2]);supports=self.inquiry_no_effect.get((self.level,self.inquiry_epoch,at,action),[])
            if len(supports)>=2:
                choices=[]
                for candidate,m in self.motions.items():
                    q=tuple(at[j]+m['delta'][j] for j in (0,1))
                    path=self.route(v,q)
                    if candidate in raw['available_actions'] and path==[candidate]:
                        choices.append((self.inquiry_visits[(self.level,self.inquiry_epoch,q)],self.trials[candidate],candidate))
                if choices:
                    proof=dict(blocked_action=action,pose=at,supports=supports[-2:],hypothesis='relocate_then_retest_a_locally_ineffective_control')
                    action=min(choices)[-1];tag='relocate_motion_inquiry'
        response=super().answer(raw,v,action,tag)
        if proof:response['certificate']['probe_relocation']=copy.deepcopy(proof)
        return response
