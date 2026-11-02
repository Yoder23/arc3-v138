"""Recover visibility from a retained template and an observed inverse control."""
import hashlib,json
from carry_interaction_learner_v10 import Controller as Base
from observed_occlusion_hypotheses import candidates

def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()

class Controller(Base):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.blind_entries={}
    def route(self,v,target,offset=None):
        original=self.blocked
        observed={(pose,action,tuple(sorted(self.positions(v)))) for (level,pose,action) in self.blind_entries if level==self.level}
        try:
            self.blocked=original|observed
            return super().route(v,target,offset)
        finally:self.blocked=original
    def answer(self,raw,v,action,tag):
        response=super().answer(raw,v,action,tag)
        entries=[dict(source=source,pose=pose,action=a) for (level,pose,a),source in self.blind_entries.items() if level==self.level]
        if entries:response['certificate']['occlusion_avoidance']=entries
        return response
    def respond(self,raw):
        response=super().respond(raw)
        if not response['done'] or raw['state']!='NOT_FINISHED' or not self.active:return response
        old=self.previous
        if not old or not old['view'] or old['raw']['state']!='NOT_FINISHED' or old['raw']['levels_completed']!=raw['levels_completed']:return response
        action=old['action'];motion=self.motions.get(action)
        if not motion:return response
        b=old['view']['body'];y,x,h,w=b['fill_box'];delta=tuple(motion['delta'])
        template=(b['fill_ink'],tuple((a,c) for a in range(h) for c in range(w)),(y,x))
        options=candidates(raw['frame'],template)
        if len(options)!=1 or tuple(options[0]['pose'][2])!=(y+delta[0],x+delta[1]):return response
        inverse=[a for a,m in self.motions.items() if tuple(m['delta'])==tuple(-v for v in delta) and a in raw['available_actions']]
        if len(inverse)!=1:return response
        self.blind_entries[(self.level,tuple(b['box'][:2]),action)]=old['t']
        proof=options[0]
        proof=dict(proof,kind='observed_occlusion_completion',source_context=digest(old['raw']),context=digest(raw),
            source_pose=template,completed_pose=proof['pose'])
        response=self.answer(raw,None,inverse[0],'restore_observability')
        response['certificate']['occlusion_recovery']=dict(source=old['t'],proof=proof)
        return response
