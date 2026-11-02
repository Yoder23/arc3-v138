"""Preserve source-observed body shapes when a selected border loses one pixel row."""
from selectable_multi_object_learner_v17 import Agent as Base
from selectable_edge_crop_v1 import crop
class Agent(Base):
    def detect_objects(self,raw):
        current=super().detect_objects(raw);f=raw['frame']
        for y in range(1,63):
            for x in range(1,63):
                if f[y][x]==self.palette or f[y-1][x]!=self.palette or f[y][x-1]!=self.palette:continue
                for h,w in sorted(self.observed_shapes):
                    q=crop(f,(y-h//3,x-w//3,h,w),self.palette)
                    if q and not any(tuple(o['box'])==tuple(q['box']) for o in current):current.append(q)
        return current
