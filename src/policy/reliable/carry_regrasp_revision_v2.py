"""Keep verified revised grasps while retiring their resolved trial budget."""
import copy
from carry_regrasp_revision_v1 import Controller as Base

class Controller(Base):
    def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self.revised_grasp_skills={}
    def record(self,raw,v):
        old=self.previous;super().record(raw,v)
        if raw['state']=='GAME_OVER' and not self.retain:self.revised_grasp_skills={}
        if not old or not v or self.held is None or not self.attachment:return
        if old['raw']['state']!=raw['state'] or raw['state']!='NOT_FINISHED' or old['raw']['levels_completed']!=raw['levels_completed']:return
        for skill in self.revised_grasp_skills.values():
            if (skill['level']==self.level and 'verified_at' not in skill and skill['pick_source']<old['t']
                and tuple(skill['new_offset'])==self.held and self.attachment['support']==old['t']):
                skill['verified_at']=old['t']
        resolved={s['release_source'] for s in self.revised_grasp_skills.values() if s['level']==self.level and 'verified_at' in s}
        # Failed branches remain in approach_failures. A successful observed
        # grip is no longer one of the three unresolved grasp experiments.
        self.regrasp_trials=[t for t in self.regrasp_trials if t['source'] not in resolved]
    def answer(self,raw,v,action,tag):
        response=super().answer(raw,v,action,tag);c=response['certificate'];revision=c.get('regrasp_revision')
        if revision and tag=='pickup':
            key=(revision['release_source'],tuple(revision['new_offset']))
            self.revised_grasp_skills.setdefault(key,dict(level=self.level,release_source=key[0],revision_source=revision['observed_at'],new_offset=key[1],pick_source=self.t-1))
        skills=[copy.deepcopy(s) for s in self.revised_grasp_skills.values() if s['level']==self.level and 'verified_at' in s]
        if skills:c['verified_revised_grasps']=skills
        return response
