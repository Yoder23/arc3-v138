"""Learn rigid translations and try remembered exact-pose goal hypotheses."""
from collections import Counter,defaultdict,deque
import copy
from visual_transform_learner import public,unique,identity,canonical,digest,fits

def nonrect(p):
    h=max(y for y,x in p[1])+1;w=max(x for y,x in p[1])+1
    return 8<=len(p[1])<h*w and h<=24 and w<=24

def eligible(obs):
    ps=[p for p in unique(obs['frame']).values() if nonrect(p)]
    return {1,2,3,4}<=set(obs['available_actions']) and any(a[0]!=b[0] and canonical(a[1])==canonical(b[1]) for a in ps for b in ps)

class Learner:
    def __init__(self):
        self.previous=None;self.rows=[];self.models=defaultdict(list);self.references={}
        self.stationary=defaultdict(list);self.failed=set();self.visits=Counter();self.pending=None;self.level=None

    def observe(self,raw,action=None):
        obs=public(raw);old=self.previous
        progress=old is not None and obs['levels_completed']!=old['levels_completed']
        if progress:
            self.rows=[];self.models=defaultdict(list);self.references={};self.stationary=defaultdict(list);self.failed=set();self.visits.clear()
        if old is not None and not progress and action not in (None,0,6) and old['state']==obs['state']=='NOT_FINISHED':
            left,right=unique(old['frame']),unique(obs['frame']);event=dict(before=copy.deepcopy(old),after=copy.deepcopy(obs),action=action)
            row=len(self.rows);self.rows.append(event)
            for key in left.keys()&right.keys():
                a,b=left[key],right[key]
                if not nonrect(a):continue
                if a[1]==b[1]:
                    delta=(b[2][0]-a[2][0],b[2][1]-a[2][1])
                    self.models[key,action].append(dict(row=row,origin=a[2],shape=a[1],delta=delta))
                if a==b:self.stationary[a].append(row)
            if self.pending:
                actor=right.get(tuple(self.pending['actor_key']))
                if actor and actor[1:]==tuple(self.pending['target'][1:]):
                    self.failed.add((self.pending['actor_key'],self.pending['target']))
        for p in unique(obs['frame']).values():
            if nonrect(p):self.references.setdefault(p,copy.deepcopy(obs))
        self.previous=copy.deepcopy(obs);self.level=obs['levels_completed'];self.pending=None

    def model(self,key,action,pose):
        samples=[s for s in self.models.get((key,action),[]) if s['shape']==pose[1]]
        moving=[s for s in samples if s['delta']!=(0,0)]
        deltas={s['delta'] for s in moving}
        if len(deltas)!=1 or len({s['origin'] for s in moving})<2:return None
        if any(s['origin']==pose[2] and s['delta']==(0,0) for s in samples):return None
        dy,dx=next(iter(deltas));nxt=(pose[0],pose[1],(pose[2][0]+dy,pose[2][1]+dx))
        support=[];origins=set()
        for s in moving:
            if s['origin'] not in origins:support.append(s['row']);origins.add(s['origin'])
            if len(support)==2:break
        return dict(after=nxt,delta=(dy,dx),support=support)

    def goal_support(self,target):
        rows=self.stationary.get(target,[]);seen=set();support=[]
        for r in rows:
            h=digest(self.rows[r]['before'])
            if h not in seen:support.append(r);seen.add(h)
            if len(support)==2:return support
        return []

    def propose(self,raw):
        obs=public(raw)
        if obs['state']!='NOT_FINISHED':return None
        current=unique(obs['frame']);legal=sorted(set(obs['available_actions'])&{1,2,3,4,5,7});plans=[]
        for key,actor in sorted(current.items()):
            if not nonrect(actor):continue
            if not any(self.model(key,a,actor) for a in legal):continue
            for target in sorted(self.references):
                if target[0]==actor[0] or target[1]!=actor[1] or (key,target) in self.failed or actor[1:]==target[1:]:continue
                support=self.goal_support(target)
                if not support:continue
                visible=current.get(identity(target))
                if visible is not None and visible!=target:continue
                # Missing target pixels denote a remembered location hypothesis.
                queue=deque([(actor,[])]);seen={actor};answer=None
                while queue and len(seen)<=4096:
                    p,path=queue.popleft()
                    if p[1:]==target[1:]:answer=path;break
                    if len(path)>=48:continue
                    for a in legal:
                        m=self.model(key,a,p)
                        if m and fits(m['after'],obs['frame']) and m['after'] not in seen:
                            seen.add(m['after']);queue.append((m['after'],path+[dict(action=a,**m)]))
                if answer:plans.append((len(answer),target,key,actor,answer,support))
        if not plans:return None
        _,target,key,actor,path,support=min(plans)
        used=sorted(set(support+[r for edge in path for r in edge['support']]))
        return dict(kind='retained_pose_alignment',action=path[0]['action'],actor=actor,actor_key=key,target=target,
            reference_observation=copy.deepcopy(self.references[target]),reference_mode='visible' if current.get(identity(target))==target else 'remembered_location',
            stationary_support=support,path=path,context=digest(obs),evidence=[dict(index=r,**copy.deepcopy(self.rows[r])) for r in used],
            scope='Tentative exact visible-shape pose alignment. Supported translations and formerly stationary reference; actual progress determines goal sufficiency.')

    def commit(self,c):self.pending=copy.deepcopy(c)

    def choose(self,raw):
        obs=public(raw)
        if obs['state']=='WIN':return None
        if obs['state'] in ('GAME_OVER','NOT_PLAYED'):return 0
        legal=sorted(set(obs['available_actions'])&{1,2,3,4,5,7})
        if not legal:return None
        a=legal[(sum(self.visits.values())//2)%len(legal)];self.visits[a]+=1;return a
