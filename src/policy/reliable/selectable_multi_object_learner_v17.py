"""Recover full tile bodies inside touching ink components using observed shapes."""
from selectable_multi_object_learner_v16 import Agent as Base
from selectable_rect_geometry_v1 import body_crop
class Agent(Base):
    def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self.observed_shapes=set()
    def reset_level(self,raw):super().reset_level(raw);self.observed_shapes=set()
    def detect_objects(self,raw):
        current=super().detect_objects(raw);self.observed_shapes.update(tuple(q['box'][2:]) for q in current);f=raw['frame'];extra=[]
        for y in range(1,63):
            for x in range(1,63):
                if f[y][x]==self.palette or f[y-1][x]!=self.palette or f[y][x-1]!=self.palette:continue
                for h,w in sorted(self.observed_shapes):
                    q=body_crop(f,(y-h//3,x-w//3,h,w),self.palette)
                    if q and not any(tuple(o['box'])==tuple(q['box']) for o in current+extra):extra.append(q)
        return current+extra
    def answer(self,*args,**kwargs):
        r=super().answer(*args,**kwargs)
        if not r['done'] and (r['action']!=6 or not r['certificate']['target']):r['certificate']['selection_point_hypothesis']=None
        return r
