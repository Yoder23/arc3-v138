"""Compose separately visible destinations using a retained successful role."""
import copy
from carry_role_transfer_v1 import Controller as Base
from carry_affordance_geometry_v2 import scene

class Controller(Base):
    def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self.distributed_goal=None
    def record(self,raw,v):
        super().record(raw,v)
        p=self.role_transfer
        if (self.goal is not None or v is None or not p or p['level']!=raw['levels_completed'] or raw['state']!='NOT_FINISHED'):return
        old=p['previous_episode']['goal'];n=v['n']
        regions=[c for c in scene(raw['frame'])['framed'] if c['inner_ink']==old['inner_ink'] and c['frame_ink']==old['frame_ink']
            and c['box'][2]%n==c['box'][3]%n==0]
        regions=sorted(regions,key=lambda c:tuple(c['box']))
        if len(regions)<2:return
        cells=[]
        for c in regions:
            y,x,h,w=c['box'];cells.extend((a,b) for a in range(y,y+h,n) for b in range(x,x+w,n))
        if len(cells)!=len(set(cells)) or len(cells)!=len(v['cargo']):return
        self.goal=dict(box=tuple(regions[0]['box']),inner_ink=old['inner_ink'],frame_ink=old['frame_ink'],observed_at=self.t,hypothesis='tile_container_with_repeated_objects')
        self.distributed_goal=dict(level=raw['levels_completed'],observed_at=self.t,regions=copy.deepcopy(regions),
            role_source=copy.deepcopy(p),hypothesis='compose_visible_regions_with_a_previously_successful_goal_role')
    def slots(self):
        out=super().slots();p=self.distributed_goal
        if p and p['level']==self.level:
            n=self.signature[0]
            for r in p['regions']:
                y,x,h,w=r['box'];out|={(a,b) for a in range(y,y+h,n) for b in range(x,x+w,n)}
        return out
    def answer(self,raw,v,action,tag):
        response=super().answer(raw,v,action,tag);p=self.distributed_goal
        if p and p['level']==raw['levels_completed']:response['certificate']['distributed_goal']=copy.deepcopy(p)
        return response
