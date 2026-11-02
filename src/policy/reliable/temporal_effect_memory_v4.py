"""Conservative visible-surface support for new latent-motion predictions."""
from collections import defaultdict
from temporal_effect_memory_v3 import Memory as BaseMemory
from temporal_effect_memory import visible

class Memory(BaseMemory):
    def __init__(self,contextual):super().__init__(contextual);self.vacated_labels=defaultdict(set)
    def observe(self,before,action,after):
        measured=super().observe(before,action,after);left,right=self.parts(before),self.parts(after)
        for key,delta in measured.items():
            if delta==(0,0):continue
            occupied={tuple(p) for p in right[key]['cells_rc']}
            self.vacated_labels[key].update(after['frame'][y][x] for y,x in left[key]['cells_rc'] if (y,x) not in occupied)
        return measured
    def predict(self,before,action):
        out=[];parts=self.parts(before);frame=before['frame'];h,w=len(frame),len(frame[0])
        for p in super().predict(before,action):
            if p['status']!='latent_action_context':out.append(p);continue
            key=(p['label'],tuple(tuple(q) for q in p['shape_rc']));allowed=self.vacated_labels[key]
            occupied={tuple(q) for q in parts[key]['cells_rc']};dy,dx=p['delta_rc'];y,x=p['origin_rc']
            destination=[(y+dy+yy,x+dx+xx) for yy,xx in p['shape_rc']]
            if not all(0<=yy<h and 0<=xx<w and ((yy,xx) in occupied or frame[yy][xx] in allowed) for yy,xx in destination):continue
            p['observed_vacated_surface_labels']=sorted(allowed)
            p['assumptions']+=['Same visible surface label supports a provisional traversability hypothesis; unobserved materials abstain']
            out.append(p)
        return out
