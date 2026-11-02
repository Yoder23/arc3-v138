"""Retain observed object-state transitions and route experiments to frontiers.

The projected state is a hypothesis, not full environment state. Conflicting
outcomes retire an edge. Every action is replanned from the next real frame.
No game identities, rewards, hidden layouts or target labels enter this module.
"""
from collections import Counter,defaultdict,deque
import copy
from visual_transform_learner import public,parts,digest

def groups(obs):
    h,w=len(obs['frame']),len(obs['frame'][0]);out=defaultdict(list)
    for color,shape,origin in parts(obs['frame']):
        dy=max(y for y,x in shape);dx=max(x for y,x in shape);y,x=origin
        if 4<=len(shape)<=100 and dy<12 and dx<12 and 0<y and 0<x and y+dy<h-1 and x+dx<w-1:
            out[(color,shape)].append(origin)
    return {k:tuple(sorted(v)) for k,v in out.items() if len(v)<=4}

def state(obs,features):
    g=groups(obs)
    return tuple((key,g.get(key,())) for key in features)

class Learner:
    def __init__(self,*,retain=True):
        self.retain=retain;self.previous=None;self.history=[];self.motion=defaultdict(list);self.origins=defaultdict(set)
        self.features=();self.epochs=[];self.selected=0;self.pending=None
        self.counts=Counter();self._graph=None

    def observe(self,raw,action=None,data=None):
        obs=public(raw);old=self.previous;data={} if data is None else data
        if old is not None:
            progress=obs['levels_completed']!=old['levels_completed'] or obs['state']=='WIN'
            reset=action==0
            if progress or reset and not self.retain:
                self.epochs.append(dict(history=len(self.history),features=len(self.features),progress=progress))
                self.history=[];self.motion=defaultdict(list);self.origins=defaultdict(set);self.features=();self._graph=None
            elif action is not None:
                event=dict(before=copy.deepcopy(old),after=copy.deepcopy(obs),action=action,data=copy.deepcopy(data))
                self.history.append(event);index=len(self.history)-1;self._graph=None
                if old['state']==obs['state']=='NOT_FINISHED' and action in (1,2,3,4,5,7):
                    left,right=groups(old),groups(obs)
                    for key in left.keys()&right.keys():
                        if len(left[key])!=len(right[key]) or left[key]==right[key]:continue
                        # A multiset can contain several coupled or mirrored actors.
                        if any(min(abs(y-u)+abs(x-v) for u,v in right[key])>16 for y,x in left[key]):continue
                        self.motion[key].append(index);self.origins[key].add(left[key])
                    features=tuple(sorted(k for k,rows in self.motion.items()
                        if len(self.origins[k])>=2))
                    if features!=self.features:
                        self.features=features;self.counts['feature_revisions']+=1
                self.counts['actual_transitions']+=1
                self.counts['resets']+=reset
        self.previous=copy.deepcopy(obs);self.pending=None

    def graph(self):
        if self._graph is not None:return self._graph
        edges=defaultdict(lambda:defaultdict(list));attempts=Counter();failures=set()
        for i,e in enumerate(self.history):
            if e['before']['state']!='NOT_FINISHED' or e['action'] not in (1,2,3,4,5,7):continue
            a=state(e['before'],self.features);b=state(e['after'],self.features);action=e['action']
            attempts[a,action]+=1
            if e['after']['state']=='GAME_OVER':failures.add((a,action));continue
            if e['after']['state']!='NOT_FINISHED':continue
            edges[(a,action)][b].append(i)
        reliable={}
        for (a,action),outcomes in edges.items():
            if len(outcomes)==1 and (a,action) not in failures:
                b,rows=next(iter(outcomes.items()))
                if b!=a:reliable[a,action]=(b,rows[0])
        self._graph=(dict(reliable),attempts,failures,sum(len(v)>1 for v in edges.values()))
        return self._graph

    def propose(self,raw):
        obs=public(raw)
        if obs['state']!='NOT_FINISHED' or not self.features:return None
        legal=tuple(sorted(set(obs['available_actions'])&{1,2,3,4,5,7}))
        if not legal:return None
        here=state(obs,self.features)
        # Do not claim an abstract control state if every tracked object vanished.
        if not any(poses for key,poses in here):return None
        graph,attempts,failures,conflicts=self.graph()
        queue=deque([(here,[])]);seen={here};options=[]
        global_counts=Counter()
        for (s,a),n in attempts.items():global_counts[a]+=n
        while queue and len(seen)<=2048:
            s,path=queue.popleft()
            for a in legal:
                if (s,a) not in failures:
                    options.append((attempts[s,a],len(path),global_counts[a],a,repr(s),path,s))
                edge=graph.get((s,a))
                if edge and edge[0] not in seen and len(path)<48:
                    seen.add(edge[0]);queue.append((edge[0],path+[dict(action=a,row=edge[1])]))
        if not options:return None
        trials,_,_,probe,_,path,target=min(options,key=lambda x:x[:5])
        action=path[0]['action'] if path else probe
        used=sorted({edge['row'] for edge in path})
        return dict(kind='retained_object_frontier',action=action,data={},context=digest(obs),
            features=self.features,current=here,target=target,path=path,probe_action=probe,
            prior_probe_attempts=trials,projection_conflicts=conflicts,
            feature_support={digest(k):self.motion[k][:] for k in self.features},
            evidence=[dict(index=i,**copy.deepcopy(self.history[i])) for i in used],
            scope='Tentative observed object-state route to an under-tested input. This does not assert a goal or a guaranteed future transition.')

    def commit(self,c):self.pending=copy.deepcopy(c);self.selected+=1

    def choose(self,raw):
        obs=public(raw)
        if obs['state']=='WIN':return None
        if obs['state'] in ('NOT_PLAYED','GAME_OVER'):return 0
        legal=sorted(set(obs['available_actions'])&{1,2,3,4,5,7})
        if not legal:return None
        # Paired trials gather effects before control authority is proposed.
        a=legal[(self.selected//2)%len(legal)];self.selected+=1;return a
