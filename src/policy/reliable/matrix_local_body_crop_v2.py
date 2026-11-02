"""Recover a pixel-verified body crop when its colors merge with adjacent scenery."""
import copy
from collections import Counter
from matrix_reference_intermediate_v5 import Agent as Base

def cropped(frame,box,ink):
    y,x,h,w=box
    if not(0<=y<=64-h and 0<=x<=64-w):return None
    counts=Counter(frame[a][b] for a in range(y,y+h) for b in range(x,x+w))
    if set(counts)!=set(ink) or len(counts)!=2 or len(set(counts.values()))!=1:return None
    parts=[]
    for color in ink:
        ps=[(a,b) for a in range(y,y+h) for b in range(x,x+w) if frame[a][b]==color];yy=min(a for a,b in ps);xx=min(b for a,b in ps);hh=max(a for a,b in ps)-yy+1;ww=max(b for a,b in ps)-xx+1
        if hh*ww!=len(ps):return None
        parts.append(dict(ink=color,box=(yy,xx,hh,ww),shape=tuple((a-yy,b-xx) for a,b in ps)))
    return dict(ink=tuple(ink),box=box,shape=tuple((dy,dx) for dy in range(h) for dx in range(w)),parts=parts)
class Agent(Base):
    def observe(self,raw):
        old=self.previous
        super().observe(raw)
        if not old or self.moving or old['action'] in (0,6,7) or old['raw']['levels_completed']!=raw['levels_completed'] or raw['state']!='NOT_FINISHED':return
        before=old['certificate'].get('moving');motion=old['certificate']['motions'].get(old['action'])
        if not before or not before.get('parts'):return
        y,x,h,w=before['box'];options=[]
        if motion:deltas=[tuple(motion['delta']),(0,0)]
        else:
            steps={abs(v) for m in old['certificate']['motions'].values() for v in m['delta'] if v}
            deltas=sorted({(0,0)}|{q for n in steps for q in ((n,0),(-n,0),(0,n),(0,-n))})
        for dy,dx in deltas:
            box=(y+dy,x+dx,h,w)
            after=cropped(raw['frame'],box,before['ink'])
            if after:options.append(after)
        if len(options)!=1:return
        after=options[0];delta=after['box'][0]-y,after['box'][1]-x
        if self.contact and any(g['box'][0]<=after['box'][0]<g['box'][0]+g['box'][2] and g['box'][1]<=after['box'][1]<g['box'][1]+g['box'][3] for g in self.goals):return
        self.contact=None
        if delta!=(0,0) and not any(old['raw']['frame'][a][b]!=raw['frame'][a][b] for a in range(y,y+h) for b in range(x,x+w)):return
        after['local_crop_support']=dict(source=old['source'],before=copy.deepcopy(before),delta=delta,prediction_mode='known_control' if motion else 'shared_observed_step_hypothesis',hypothesis='same_palette_body_at_observed_control_prediction')
        self.moving=after
        if delta!=(0,0):self.motions[old['action']]=dict(delta=delta,support=old['source'],before=before,after=copy.deepcopy(after))
        else:self.blocked.add(((y,x),old['action'],self.program_index))
