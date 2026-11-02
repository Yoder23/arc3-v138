"""Recover an observed rigid footprint when translated objects touch and merge in color."""
import copy
from selectable_passive_contact_learner_v2 import Agent as Base
class Agent(Base):
    def candidates(self,raw):
        result=super().candidates(raw);state=self.passive_probe_state
        if not state or not state.get('contact'):return result
        p=state['contact'];old=p['target'];m=self.motions.get(p['action'])
        if not m:return result
        shapes=[(q,tuple(q['box'][:2])) for q in p['candidates']]
        dy,dx=m['delta']
        for k in range(1,64):shapes.append((old,(old['box'][0]+k*dy,old['box'][1]+k*dx)))
        for q,pos in shapes:
            if min(pos)<0 or pos[0]+q['box'][2]>64 or pos[1]+q['box'][3]>64:continue
            if not all(raw['frame'][pos[0]+a][pos[1]+b]==q['ink'] for a,b in q['shape']):continue
            box=(*pos,*q['box'][2:])
            if any(tuple(r['box'])==box and r['ink']==q['ink'] for r in result):continue
            r=copy.deepcopy(q);r['box']=box;r['segmentation_is_hypothesis']=True;result.append(r)
        return result
