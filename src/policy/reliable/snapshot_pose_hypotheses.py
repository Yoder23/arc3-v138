"""Learn rigid translations and try remembered exact-pose goal hypotheses."""
from collections import Counter,defaultdict,deque
from retained_body_memory_v2 import Memory
import copy
from visual_transform_learner import public,unique,identity,canonical,digest,fits

def nonrect(p):
    h=max(y for y,x in p[1])+1;w=max(x for y,x in p[1])+1
    return 8<=len(p[1])<h*w and h<=24 and w<=24

def eligible(obs):
    ps=[p for p in unique(obs['frame']).values() if nonrect(p)]
    return {1,2,3,4}<=set(obs['available_actions']) and any(a[0]!=b[0] and canonical(a[1])==canonical(b[1]) for a in ps for b in ps)


def propose(learner,raw):
    obs=public(raw)
    if obs['state']!='NOT_FINISHED':return None
    current=learner.perceive(obs['frame']);legal=sorted(set(obs['available_actions'])&{1,2,3,4,5,7});plans=[]
    for key,actor in sorted(current.items()):
        if not nonrect(actor):continue
        if not any(learner.model(key,a,actor) for a in legal):continue
        for target in sorted(learner.references):
            if target[0]==actor[0] or target[1]!=actor[1] or (key,target) in learner.failed or actor[1:]==target[1:]:continue
            support=[]
            visible=current.get(identity(target))
            if visible is not None and visible!=target:continue
            # Missing target pixels denote a remembered location hypothesis.
            queue=deque([(actor,[])]);seen={actor};answer=None
            while queue and len(seen)<=4096:
                p,path=queue.popleft()
                if p[1:]==target[1:]:answer=path;break
                if len(path)>=48:continue
                for a in legal:
                    m=learner.model(key,a,p)
                    if m and fits(m['after'],obs['frame']) and m['after'] not in seen:
                        seen.add(m['after']);queue.append((m['after'],path+[dict(action=a,**m)]))
            if answer:plans.append((len(answer),target,key,actor,answer,support))
    if not plans:return None
    _,target,key,actor,path,support=min(plans)
    used=sorted(set(support+[r for edge in path for r in edge['support']]))
    result=dict(kind='retained_pose_alignment',action=path[0]['action'],actor=actor,actor_key=key,target=target,
        reference_observation=copy.deepcopy(learner.references[target]),reference_mode='visible' if current.get(identity(target))==target else 'remembered_location',
        stationary_support=support,path=path,context=digest(obs),evidence=[dict(index=r,**copy.deepcopy(learner.rows[r])) for r in used],
        scope='Tentative alignment to an actually observed congruent shape. Translation evidence is required; stationarity and goal sufficiency are unproven. Only actual completion feedback may refute this goal.')

    result['reference_evidence_basis']='single_observed_shape_hypothesis'
    result['motion_context_boundary']=copy.deepcopy(learner.boundary)
    if learner.body_memory.templates:result['body_completion_sources']=learner.body_memory.sources()
    return result
