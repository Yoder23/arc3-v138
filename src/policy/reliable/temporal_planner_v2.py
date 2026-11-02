"""Temporal planner with measured collision-driven contact-hypothesis revision."""
from temporal_planner import TemporalPlanner as Base
from temporal_effect_memory import visible
from evidence import observation, digest

class TemporalPlanner(Base):
    def __init__(self,**kwargs):
        super().__init__(**kwargs);self.contact_blocked=set();self.contact_revisions=[]

    def temporal_route(self,obs,part,models,target):
        if target['label'] in self.contact_blocked:return None
        return super().temporal_route(obs,part,models,target)

    def run(self,initial,step,*,max_actions=256):
        current=observation(initial)
        def measured_step(action):
            nonlocal current
            after=observation(step(action));decision=self.decisions[-1]
            if current['levels_completed']!=after['levels_completed'] or after['state']!='NOT_FINISHED':self.contact_blocked.clear()
            elif decision['temporal']:
                key=(decision['actor']['label'],tuple(tuple(p) for p in decision['actor']['shape_rc']))
                left,right=self.temporal.parts(current).get(key),self.temporal.parts(after).get(key)
                if left and right:
                    dy=right['origin_rc'][0]-left['origin_rc'][0];dx=right['origin_rc'][1]-left['origin_rc'][1]
                    if (dy,dx)==(0,0) and decision['prediction']['delta_rc']!=[0,0]:
                        y,x=left['origin_rc'];py,px=decision['prediction']['delta_rc'];shape=left['shape_rc'];f=current['frame']
                        labels={f[y+py+r][x+px+c] for r,c in shape if 0<=y+py+r<len(f) and 0<=x+px+c<len(f[0])}
                        if labels=={decision['target']['label']}:
                            self.contact_blocked.update(labels);self.contact_revisions.append(dict(step=self.action_count,kind='contact_material_provisionally_rejected',labels=sorted(labels),evidence_hash=digest(dict(before=current,action=action,after=after))))
                    elif (dy,dx)!=(0,0):
                        old={tuple(p) for p in left['cells_rc']};entered={current['frame'][r][c] for r,c in right['cells_rc'] if (r,c) not in old}
                        for label in entered & self.contact_blocked:
                            self.contact_blocked.remove(label);self.contact_revisions.append(dict(step=self.action_count,kind='contact_rejection_refuted',label=label))
            current=after;return after
        result=super().run(initial,measured_step,max_actions=max_actions);result['contact_revisions']=self.contact_revisions[:];return result
