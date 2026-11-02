"""Recover a known body at an observed primitive-motion prediction with two adjacent missing edges."""
import copy,itertools
from selectable_multi_passive_inquiry_v3 import Agent as Base
class Agent(Base):
    def detect_objects(self,raw):
        current=super().detect_objects(raw);old=self.previous
        if not old:return current
        b=next((b for b in old['objects'] if tuple(b['box'])==tuple(self.active_box or ())),None);m=self.motions.get(old['action'])
        if not b or not m:return current
        expected=tuple(b['box'][i]+m['delta'][i] for i in (0,1))
        if any(tuple(q['box'][:2]) in (tuple(b['box'][:2]),expected) and tuple(q['box'][2:])==tuple(b['box'][2:]) for q in current):return current
        y,x,h,w=b['box'];options=[]
        for dy,dx in dict.fromkeys([tuple(m['delta']),(0,0)]):
            yy,xx=y+dy,x+dx
            if not(0<=yy<=64-h and 0<=xx<=64-w):continue
            center=raw['frame'][yy+h//2][xx+w//2]
            if center==self.palette or center!=b['center']:continue
            for vertical,horizontal in itertools.product(('top','bottom'),('left','right')):
                row=0 if vertical=='top' else h-1;col=0 if horizontal=='left' else w-1
                if all(raw['frame'][yy+a][xx+z]==(center if a==row or z==col or h//3<=a<2*h//3 and w//3<=z<2*w//3 else self.palette) for a in range(h) for z in range(w)):
                    options.append(dict(box=(yy,xx,h,w),ink=self.palette,center=center,tile_body=True,corner_occlusion=[vertical,horizontal],visible_shape_is_hypothesis=True,partial_crop_support=dict(source=old['source'],before=copy.deepcopy(b),delta=(dy,dx))))
        return current+options if len(options)==1 else current
