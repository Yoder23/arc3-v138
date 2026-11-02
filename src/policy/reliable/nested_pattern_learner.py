"""Retain example-grounded rules and learn click effects only from actual transitions."""
import copy
from collections import Counter
from nested_pattern_hypotheses import candidates
from nested_pattern_perception import representations
from visual_transform_learner import public,digest

class Learner:
    def __init__(self):
        self.memory=[];self.previous=None;self.current=[];self.samples=[];self.visits=Counter()
        self.failed=set();self.pending=None;self.level=None;self.rows=[]

    def observe(self,raw,last=None,data=None):
        obs=public(raw);data=data or {};h=digest(obs)
        if self.previous is not None and last is not None:
            before=self.previous;self.rows.append(dict(before=digest(before),after=h,action=last,data=dict(data)))
            progress=obs['levels_completed']>before['levels_completed']
            if progress:
                self.failed.clear();self.visits.clear();self.pending=None
            elif last==0:
                self.visits.clear();self.pending=None
            elif last==6 and before['state']=='NOT_FINISHED':
                a=before['frame'];b=obs['frame']
                changes=[(y,x) for y in range(len(a)) for x in range(len(a[0])) if a[y][x]!=b[y][x]]
                if changes:
                    y=min(p[0] for p in changes);x=min(p[1] for p in changes)
                    height=max(p[0] for p in changes)-y+1;width=max(p[1] for p in changes)-x+1
                    if height==width and len(changes)==height*width and y<=data.get('y',-1)<y+height and x<=data.get('x',-1)<x+width:
                        old={a[yy][xx] for yy,xx in changes};new={b[yy][xx] for yy,xx in changes}
                        if len(old)==len(new)==1:
                            self.samples.append(dict(row=len(self.rows)-1,box=(y,x,height,width),old=next(iter(old)),new=next(iter(new))))
                if self.pending and all(b[y][x]==v for y,x,v in self.pending['desired']):
                    self.failed.add(tuple(self.pending['rule']))
                self.pending=None
        parsed=candidates(obs['frame'],self.memory)
        for p in parsed:
            if p['live'] and not any(tuple(m['rule'])==tuple(p['rule']) for m in self.memory):
                self.memory.append(dict(rule=tuple(p['rule']),examples=copy.deepcopy(p['examples']),source=h))
        self.current=parsed;self.previous=copy.deepcopy(obs);self.level=obs['levels_completed']

    def propose(self,raw):
        obs=public(raw)
        if obs['state']!='NOT_FINISHED' or 6 not in obs['available_actions']:return None
        for p in self.current:
            if tuple(p['rule']) in self.failed:continue
            size=p['scene']['size'];m=next((m for m in self.memory if tuple(m['rule'])==tuple(p['rule'])),None)
            if m is None:continue
            choices=[(self.visits[(self.level,y,x)],y,x,c,p['desired'][y,x]) for y,x,c in p['scene']['cells'] if c!=p['desired'][y,x]]
            if not choices:continue
            _,y,x,old,new=min(choices);support=[];origins=set()
            for s in self.samples:
                key=tuple(s['box'][:2])
                if key not in origins:origins.add(key);support.append(s['row'])
                if len(support)==2:break
            return dict(kind='nested_pattern',action=6,data=dict(x=x+size//2,y=y+size//2),
                rule=tuple(p['rule']),source=m['source'],examples=copy.deepcopy(m['examples']),
                scene=copy.deepcopy(p['scene']),desired=[(y,x,v) for (y,x),v in sorted(p['desired'].items())],
                box=(y,x,size,size),old=old,expected=new,control_support=support if len(support)==2 else [],
                control_mode='learned_toggle_hypothesis' if len(support)==2 else 'uncertain_probe',
                control_evidence=[copy.deepcopy(self.rows[i]) for i in support] if len(support)==2 else [])
        return None

    def commit(self,certificate):
        self.pending=copy.deepcopy(certificate);y,x,_,_=certificate['box'];self.visits[self.level,y,x]+=1

    def choose(self,raw):
        obs=public(raw)
        if obs['state']=='WIN':return None,{}
        if obs['state']=='GAME_OVER':return 0,{}
        scenes=representations(obs['frame'])
        if 6 in obs['available_actions'] and scenes:
            size=scenes[0]['size'];y,x,_=min(scenes[0]['cells'],key=lambda p:(self.visits[self.level,p[0],p[1]],p))
            self.visits[self.level,y,x]+=1
            return 6,dict(x=x+size//2,y=y+size//2)
        return None,{}
