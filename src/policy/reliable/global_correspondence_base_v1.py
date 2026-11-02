"""Learn observed token permutations and compose jointly marked goals after failure."""
from collections import Counter,deque
import copy
from segmented_track_geometry_v1 import scenes,permutations,apply,read
from visual_transform_learner import public
from global_token_correspondence_v1 import constraints

class Learner:
    def __init__(self,retain=True):
        self.retain=retain;self.previous=None;self.history=[];self.level=None
        self.goals={};self.models={};self.trials=Counter();self.refuted=set();self.revisions=[]
    def observe(self,raw,action=None,data=None):
        obs=public(raw);before=self.previous;index=len(self.history)
        if before is not None and action is not None:self.history.append(dict(before=before,after=copy.deepcopy(obs),action=action,data=copy.deepcopy(data or {})))
        boundary=self.level is not None and obs['levels_completed']!=self.level
        forget=not self.retain and obs['state']=='GAME_OVER'
        if boundary or forget:
            self.goals={};self.models={};self.trials=Counter();self.refuted=set()
        if before is not None and action==6 and before['state']=='NOT_FINISHED' and not boundary and not forget:
            point=(data.get('x'),data.get('y'))
            for scene in scenes(before['frame']):
                k=scene['cells'];after=read(obs['frame'],k)
                if after is None:continue
                if not any(c['point']==point for c in scene['controls']):continue
                key=k,point;self.trials[key]+=1
                past=self.models.get(key)
                allowed,permutation,radius=constraints(k,scene['word'],after,past['allowed'] if past else None)
                support=past['support']+[index] if past else [index]
                if permutation is None and past:
                    self.revisions.append(dict(event=index,point=point,prior_support=past['support'],reason='Actual outcome contradicts the retained global correspondence constraints'))
                    allowed,permutation,radius=constraints(k,scene['word'],after)
                    support=[index]
                possible={} if permutation is None else {permutation:dict(mapping='observed_global_correspondence',radius_squared=radius)}
                self.models[key]=dict(candidates=possible,support=support,allowed=allowed)
                goals=self.goals.get(k,[])
                # Partial alignment never retires a conjunction. Only its full
                # observed achievement without progress refutes this goal set.
                if goals and all(after[g['index']]==g['ink'] for g in goals) and obs['state']=='NOT_FINISHED':self.refuted.add(k)
        self.level=obs['levels_completed']
        if obs['state']=='NOT_FINISHED':
            for scene in scenes(obs['frame']):
                if scene['goals'] and scene['cells'] not in self.goals:
                    self.goals[scene['cells']]=[dict(copy.deepcopy(g),observed_at=len(self.history)) for g in scene['goals']]
        self.previous=copy.deepcopy(obs)
    def propose(self,raw):
        obs=public(raw)
        if obs['state']=='WIN':return None
        if obs['state']=='GAME_OVER':return dict(kind='track_reset',action=0,data={})
        if 6 not in obs['available_actions']:return None
        for scene in scenes(obs['frame']):
            key=scene['cells'];goals=self.goals.get(key,[])
            if not goals or key in self.refuted or not scene['controls']:continue
            models=[];unknown=[]
            for c in scene['controls']:
                m=self.models.get((key,c['point']))
                if m and len(m['candidates'])==1:
                    perm,shape=next(iter(m['candidates'].items()))
                    models.append(dict(control=c,permutation=perm,**shape,support=m['support']))
                else:unknown.append(c)
            inks={g['ink'] for g in goals};state=tuple(v if v in inks else -1 for v in scene['word'])
            queue=deque([(state,[])]);seen={state};route=None
            while queue and len(seen)<=20000:
                current,path=queue.popleft()
                if path and all(current[g['index']]==g['ink'] for g in goals):route=path;break
                if len(path)>=32:continue
                for m in models:
                    nxt=apply(current,m['permutation'])
                    if nxt not in seen:seen.add(nxt);queue.append((nxt,path+[m]))
            if route:
                first=route[0];c=first['control']
                return dict(kind='track_conjunction_plan',action=6,data=dict(zip(('x','y'),c['point'])),
                    scene=copy.deepcopy(scene),goals=copy.deepcopy(goals),control=copy.deepcopy(c),route=copy.deepcopy(route),
                    predicted_word=apply(scene['word'],first['permutation']),tentative_goal=True,search_states=len(seen))
            c=min(unknown or scene['controls'],key=lambda c:(self.trials[key,c['point']],c['box']))
            return dict(kind='track_control_probe',action=6,data=dict(zip(('x','y'),c['point'])),
                scene=copy.deepcopy(scene),goals=copy.deepcopy(goals),control=copy.deepcopy(c),route=[],predicted_word=None,
                tentative_goal=True,search_states=len(seen))
        return None

class Controller:
    def __init__(self,prior=None,retain=True):
        self.prior=prior;self.learner=Learner(retain);self.active=False;self.last=None;self.data={};self.steps=0
    def respond(self,raw):
        obs=public(raw)
        if not self.active and self.prior is not None:
            ready=obs['state']=='NOT_FINISHED' and 6 in obs['available_actions'] and any(s['goals'] and s['controls'] for s in scenes(obs['frame']))
            if not ready:return self.prior.respond(obs)
        self.learner.observe(obs,self.last,self.data);c=self.learner.propose(obs)
        if c and c['kind']!='track_reset':self.active=True
        self.steps+=int(c is not None)
        response=dict(done=c is None,action=c['action'] if c else 0,data=c['data'] if c else {},certificate=c,
            advisor='observed_local_token_correspondence',diagnostics=dict(actual_model_calls=0,track_actions=self.steps))
        self.last=response['action'];self.data=copy.deepcopy(response['data']);return response
