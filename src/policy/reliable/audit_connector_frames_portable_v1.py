"""Scalar/pixel checks of selected composite control predictions and provenance."""
from collections import Counter
import hashlib,json
import numpy as np

def freeze(v):
    if isinstance(v,(list,tuple)):return tuple(freeze(x) for x in v)
    return v
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def key(obj):return freeze(obj['shape']),freeze(obj['origin'])
def transformed(shape,turn):
    h=max(y for y,x,c in shape)+1;w=max(x for y,x,c in shape)+1
    a=np.full((h,w),-1,dtype=int)
    for y,x,c in shape:a[y,x]=c
    a=np.rot90(a,turn)
    return tuple(sorted((int(y),int(x),int(a[y,x])) for y,x in zip(*np.where(a>=0))))
def canonical(shape):return min(transformed(shape,k) for k in range(4))
def pixels(obs,obj):
    shape,origin=key(obj)
    return all(0<=y+origin[0]<len(obs['frame']) and 0<=x+origin[1]<len(obs['frame'][0])
               and obs['frame'][y+origin[0]][x+origin[1]]==c for y,x,c in shape)
def apply(obj,rule):
    shape,(y,x)=key(obj);mode,turn,dy,dx=rule;after=transformed(shape,turn)
    if mode=='center2':
        cy=2*y+max(a for a,b,c in shape);cx=2*x+max(b for a,b,c in shape)
        yy=cy+dy-max(a for a,b,c in after);xx=cx+dx-max(b for a,b,c in after)
    elif mode=='origin2':yy=2*y+dy;xx=2*x+dx
    else:raise AssertionError('Unsupported coordinate frame')
    assert yy%2==0 and xx%2==0
    return dict(obj,shape=after,origin=(yy//2,xx//2))

def extract(frame,signature):
    # Exhaustive bounding-box colored-mask search, independent of component code.
    n=Counter(c for y,x,c in signature);anchor=min(n,key=lambda c:(-n[c],c))
    f=np.asarray(frame);coords=np.argwhere(f==anchor)
    if not len(coords):return []
    # Independent four-neighbor flood fill; no SDK-specific binary dependency.
    remaining=set(map(tuple,coords.tolist()));boxes=[];out=[]
    while remaining:
        start=min(remaining);remaining.remove(start);todo=[start];cells=[]
        while todo:
            y,x=todo.pop();cells.append((y,x))
            for q in ((y-1,x),(y+1,x),(y,x-1),(y,x+1)):
                if q in remaining:remaining.remove(q);todo.append(q)
        boxes.append((slice(min(y for y,x in cells),max(y for y,x in cells)+1),slice(min(x for y,x in cells),max(x for y,x in cells)+1)))
    for box in boxes:
        for t in range(4):
            s=transformed(signature,t);ay=min(y for y,x,c in s if c==anchor);ax=min(x for y,x,c in s if c==anchor)
            obj=dict(shape=s,origin=(box[0].start-ay,box[1].start-ax))
            if pixels(dict(frame=frame),obj) and key(obj) not in [key(o) for o in out]:out.append(obj)
    return out

class Audit:
    def __init__(self):self.events={};self.counts=Counter();self.checked={}
    def evidence(self,h,signature,rules):
        cache=(h,freeze(signature),freeze(rules))
        if cache not in self.checked:
            e=self.events[h]
            left=extract(e['before']['frame'],signature);right=extract(e['after']['frame'],signature)
            assert len(left)==len(right)==1
            for rule in rules:assert key(apply(left[0],rule))==key(right[0])
            self.checked[cache]=key(left[0])
        return self.checked[cache]
    def check(self,event):
        before,after,action=event['before'],event['after'],event['action'];c=event.get('certificate')
        assert action==0 or action in before['available_actions']
        if c:
            assert c['action']==action and c['context']==digest(before)
            actor=c['actor'];assert pixels(before,actor)
            assert canonical(actor['shape'])==freeze(c['actor_identity'])
            assert c['path'] and c['path'][0]['action']==action
            here=actor
            for edge in c['path']:
                origins=set();assert edge['support'] and edge['rules']
                for h in edge['support']:
                    e=self.events[h];assert e['action']==edge['action']
                    origins.add(self.evidence(h,c['actor_identity'],edge['rules']))
                assert len(origins)>=2
                for rule in edge['rules']:assert key(apply(here,rule))==key(edge['predicted'])
                here=edge['predicted']
            assert key(here)==key(c['goal'])
            assert pixels(before,c['goal']['target'])
            predicted=c['path'][0]['predicted']
            if after['state']=='NOT_FINISHED' and after['levels_completed']==before['levels_completed']:
                visible=extract(after['frame'],c['actor_identity'])
                if len(visible)==1:
                    self.counts['forecast_correct' if key(visible[0])==key(predicted) else 'forecast_refuted']+=1
                else:self.counts['identity_unknown']+=1
            self.counts['plans']+=1
        h=digest(dict(before=before,action=action,after=after));self.events[h]=event;self.counts['events']+=1
        return True
