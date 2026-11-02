"""Observed geometric controls and revisable visible-object goal hypotheses.

Authored geometry priors, not a neural or biological model. Only four public
observation fields enter. A hypothesis never becomes a supplied goal label.
"""
from collections import Counter, defaultdict, deque
from functools import lru_cache
import hashlib
import json
import numpy as np
from scipy import ndimage


def digest(x):
    return hashlib.sha256(json.dumps(x, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


@lru_cache(maxsize=4096)
def transform(shape, mirror, turn):
    h=max(y for y,x in shape)+1; w=max(x for y,x in shape)+1
    a=np.zeros((h,w),dtype=bool)
    for y,x in shape:a[y,x]=True
    a=np.rot90(np.fliplr(a) if mirror else a, turn)
    return tuple(map(tuple,np.argwhere(a).tolist()))


def canonical(shape):
    return min(transform(shape,m,t) for m in (False,True) for t in range(4))


@lru_cache(maxsize=64)
def _parts(frame):
    a=np.asarray(frame); bg=int(np.bincount(a.ravel()).argmax()); out=[]
    for color in np.unique(a):
        if color==bg:continue
        lab,_=ndimage.label(a==color)
        for i,s in enumerate(ndimage.find_objects(lab),1):
            if s is None:continue
            shape=tuple(map(tuple,np.argwhere(lab[s]==i).tolist()))
            if not 2<=len(shape)<a.size//4:continue
            out.append((int(color),shape,(s[0].start,s[1].start)))
    return tuple(sorted(out))


def parts(frame):return _parts(tuple(map(tuple,frame)))
def identity(p):return (p[0],canonical(p[1]))
def unique(frame):
    grouped=defaultdict(list)
    for p in parts(frame):grouped[identity(p)].append(p)
    return {k:v[0] for k,v in grouped.items() if len(v)==1}


def apply(p, rule):
    mirror,turn,dy,dx=rule
    return (p[0],transform(p[1],mirror,turn),(p[2][0]+dy,p[2][1]+dx))


def fits(p,frame):
    h,w=len(frame),len(frame[0]); y,x=p[2]
    return all(0<=y+dy<h and 0<=x+dx<w for dy,dx in p[1])


def public(raw):
    if set(raw)!={'frame','state','levels_completed','available_actions'}:raise ValueError('Extra observation field')
    f=raw['frame'];assert f and f[0] and len(f)<=64 and len(f[0])<=64
    assert all(len(row)==len(f[0]) and all(type(x) is int and 0<=x<16 for x in row) for row in f)
    assert raw['state'] in ('NOT_PLAYED','NOT_FINISHED','GAME_OVER','WIN')
    assert type(raw['levels_completed']) is int and raw['levels_completed']>=0
    assert len(set(raw['available_actions']))==len(raw['available_actions'])
    return raw


class Learner:
    def __init__(self, *, shape_goals=True, retain_failures=True):
        self.shape_goals=shape_goals;self.retain_failures=retain_failures
        self.models={};self.rows=[];self.trials=Counter();self.visits=Counter()
        self.previous=None;self.last_action=None;self.level=None;self.pending_goal=None
        self.failed=set();self.epochs=[];self.actor=None;self.certificate=None
        self.steps=0;self.episode=0;self.failures=0;self.refutations=0

    def clear(self, keep_failures):
        self.epochs.append(dict(episode=self.episode,rows=len(self.rows)))
        self.models={};self.rows=[];self.trials.clear();self.visits.clear();self.actor=None
        self.pending_goal=None;self.episode+=1
        if not keep_failures:self.failed.clear()

    def observe(self, raw, action=None):
        obs=public(raw); self.certificate=None
        if self.previous is not None:
            old=self.previous; progress=obs['levels_completed']>old['levels_completed'] or obs['state']=='WIN'
            boundary=progress or action==0
            if boundary:self.clear(keep_failures=not progress and self.retain_failures)
            elif old['state']=='NOT_FINISHED' and obs['state']=='NOT_FINISHED' and action in (1,2,3,4,5,7):
                left,right=unique(old['frame']),unique(obs['frame'])
                event=dict(before=old,action=action,after=obs); evidence=digest(event)
                for key in sorted(left.keys() & right.keys()):
                    a,b=left[key],right[key]
                    rules={(m,t,b[2][0]-a[2][0],b[2][1]-a[2][1]) for m in (False,True) for t in range(4) if transform(a[1],m,t)==b[1]}
                    if not rules:continue
                    model=self.models.setdefault((key,action),dict(rules=None,support=[],origins=set(),changed=False,conflict=False))
                    if model['rules'] is not None:rules &= model['rules']
                    if not rules and not model['conflict']:self.refutations+=1
                    model['rules']=rules;model['conflict']=not rules
                    model['support'].append(evidence);model['origins'].add((a[1],a[2]))
                    model['changed'] |= a!=b
                self.rows.append(event)
                if self.pending_goal is not None and not progress:
                    key,goal=self.pending_goal
                    if key in right and self.reached(right[key],goal):
                        self.failed.add((old['levels_completed'],key,goal));self.failures+=1
            self.pending_goal=None
        self.previous=json.loads(json.dumps(obs));self.level=obs['levels_completed']

    def supported(self,key,action,p):
        m=self.models.get((key,action))
        if not m or len(m['origins'])<2 or not m['rules']:return None
        results={apply(p,r) for r in m['rules']}
        return next(iter(results)) if len(results)==1 else None

    @staticmethod
    def reached(p, goal):
        kind,color,shape,origin=goal
        if kind=='shape':return p[1]==shape
        cells={(y+origin[0],x+origin[1]) for y,x in shape}
        return any((y+p[2][0],x+p[2][1]) in cells for y,x in p[1])

    def goals(self,p,obs):
        out=[];key=identity(p)
        for q in parts(obs['frame']):
            if q==p:continue
            if self.shape_goals and canonical(q[1])==canonical(p[1]) and q[1]!=p[1]:
                out.append(('shape',q[0],q[1],q[2]))
            out.append(('contact',q[0],q[1],q[2]))
        return [g for g in out if (obs['levels_completed'],key,g) not in self.failed and not self.reached(p,g)]

    def search(self,p,goal,legal,obs):
        key=identity(p);todo=deque([(p,[])]);seen={p}
        while todo and len(seen)<=512:
            here,path=todo.popleft()
            if path and self.reached(here,goal):return path
            if len(path)>=12:continue
            for action in legal:
                nxt=self.supported(key,action,here)
                if nxt is not None and nxt not in seen and fits(nxt,obs['frame']):
                    seen.add(nxt);todo.append((nxt,path+[action]))
        return None

    def choose(self, raw):
        obs=public(raw);self.certificate=None
        if obs['state']=='WIN':return None
        if obs['state'] in ('GAME_OVER','NOT_PLAYED'):return 0
        legal=sorted(set(obs['available_actions']) & {1,2,3,4,5,7})
        if not legal:return None
        candidates=[];objects=unique(obs['frame'])
        for key,p in objects.items():
            changed=sum(m['changed'] and bool(m['rules']) for (k,a),m in self.models.items() if k==key)
            if changed:candidates.append((-changed,key,p))
        if candidates:
            _,key,p=min(candidates);self.actor=key;plans=[]
            for goal in self.goals(p,obs):
                path=self.search(p,goal,legal,obs)
                if path:plans.append((goal[0]!='shape',len(path),goal,path))
            if plans:
                _,_,goal,path=min(plans);action=path[0];pred=self.supported(key,action,p)
                model=self.models[(key,action)]
                self.certificate=dict(actor=p,action=action,predicted=pred,goal=goal,
                    rules=sorted(model['rules']),support=list(model['support']),episode=self.episode)
                self.pending_goal=(key,goal);return self.selected(action,obs)
        # Acquire contrasting effects separately from goal discrimination.
        scene=tuple((p[0],p[1],p[2]) for p in parts(obs['frame']))
        action=min(legal,key=lambda a:(self.trials[(scene,a)],sum(n for (s,b),n in self.trials.items() if b==a),a))
        return self.selected(action,obs)

    def selected(self, action, obs):
        scene=tuple((p[0],p[1],p[2]) for p in parts(obs['frame']))
        self.trials[(scene,action)]+=1;self.steps+=1
        return action
