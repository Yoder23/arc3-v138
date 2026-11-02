"""Tentative assembly goals for rigid multi-color objects with repeated connectors."""
from collections import Counter,defaultdict
from functools import lru_cache
import copy,heapq
import numpy as np
from scipy import ndimage
from visual_transform_learner import public,digest


def normalize(cells):
    y=min(p[0] for p in cells);x=min(p[1] for p in cells)
    return tuple(sorted((a-y,b-x,c) for a,b,c in cells))


@lru_cache(maxsize=8192)
def rotate(shape,k):
    cells=shape
    for _ in range(k%4):
        h=max(y for y,x,c in cells)+1;w=max(x for y,x,c in cells)+1
        cells=tuple((w-1-x,y,c) for y,x,c in cells)
    return normalize(cells)


def identity(obj):
    return min(rotate(obj['shape'],k) for k in range(4))


def objects(frame):
    a=np.asarray(frame);bg=int(np.bincount(a.ravel()).argmax())
    labels,_=ndimage.label(a!=bg);result=[]
    for i,box in enumerate(ndimage.find_objects(labels),1):
        if box is None:continue
        if box[0].start==0 or box[1].start==0 or box[0].stop==len(a) or box[1].stop==a.shape[1]:continue
        coords=np.argwhere(labels[box]==i);counts=Counter(int(a[y+box[0].start,x+box[1].start]) for y,x in coords)
        if not 2<=len(counts)<=4 or len(coords)>=a.size//4:continue
        color=min(counts,key=lambda c:(-counts[c],c))
        shape=tuple(sorted((int(y),int(x),int(a[y+box[0].start,x+box[1].start])) for y,x in coords))
        if counts[color]<2*min(counts.values()):continue
        result.append(dict(shape=shape,origin=(box[0].start,box[1].start),body=color))
    return sorted(result,key=lambda o:(o['origin'],o['shape']))


def ports(obj):
    h=max(y for y,x,c in obj['shape'])+1;w=max(x for y,x,c in obj['shape'])+1
    out={}
    for color in sorted({c for y,x,c in obj['shape']} - {obj['body']}):
        mask=np.zeros((h,w),dtype=bool)
        for y,x,c in obj['shape']:
            if c==color:mask[y,x]=True
        labs,n=ndimage.label(mask)
        if not 2<=n<=6:continue
        parts=[tuple(map(tuple,np.argwhere(labs==i).tolist())) for i in range(1,n+1)]
        if len({len(p) for p in parts})!=1:continue
        cells=tuple(sorted(p for part in parts for p in part))
        out[color]=cells
    return out


def hypotheses(actor,others):
    """Only geometry is asserted; actual progress must establish a goal."""
    result=[];origin=actor['origin']
    for target in others:
        if identity(actor)==identity(target):continue
        target_ports=ports(target)
        for turn in range(4):
            shape=rotate(actor['shape'],turn);turned=dict(actor,shape=shape)
            for color,cells in ports(turned).items():
                if color not in target_ports:continue
                refs=target_ports[color]
                def norm(ps):
                    y=min(p[0] for p in ps);x=min(p[1] for p in ps)
                    return tuple(sorted((a-y,b-x) for a,b in ps))
                if norm(cells)!=norm(refs):continue
                # Candidate face-to-face offsets derive from visible port dimensions.
                arr=np.zeros((max(y for y,x in cells)+1,max(x for y,x in cells)+1),dtype=bool)
                for y,x in cells:arr[y,x]=True
                lab,_=ndimage.label(arr);patch=ndimage.find_objects(lab)[0]
                ph=patch[0].stop-patch[0].start;pw=patch[1].stop-patch[1].start
                for dy,dx in ((ph,0),(-ph,0),(0,pw),(0,-pw)):
                    shift=(target['origin'][0]+min(y for y,x in refs)-min(y for y,x in cells)+dy,
                           target['origin'][1]+min(x for y,x in refs)-min(x for y,x in cells)+dx)
                    ac={(y+shift[0],x+shift[1]) for y,x,c in shape}
                    tc={(y+target['origin'][0],x+target['origin'][1]) for y,x,c in target['shape']}
                    if ac&tc:continue
                    contacts={(y,x) for y,x in ac if any((y+a,x+b) in tc for a,b in ((1,0),(-1,0),(0,1),(0,-1)))}
                    pc={(y+shift[0],x+shift[1]) for y,x in cells}
                    if not contacts or not contacts<=pc:continue
                    actor_colors={(y+shift[0],x+shift[1]):v for y,x,v in shape}
                    target_colors={(y+target['origin'][0],x+target['origin'][1]):v for y,x,v in target['shape']}
                    pairs=[(actor_colors[y,x],target_colors[y+a,x+b]) for y,x in actor_colors
                           for a,b in ((1,0),(-1,0),(0,1),(0,-1)) if (y+a,x+b) in target_colors]
                    if not pairs or any(a!=color or b!=color for a,b in pairs):continue
                    result.append(dict(shape=shape,origin=shift,connector_color=color,
                        target=target,scope='Geometrically compatible connector contact; tentative goal.'))
    return result


def center2(obj):
    return (2*obj['origin'][0]+max(y for y,x,c in obj['shape']),
            2*obj['origin'][1]+max(x for y,x,c in obj['shape']))


def apply(obj,rule):
    turn,dy,dx=rule;shape=rotate(obj['shape'],turn);cy,cx=center2(obj)
    y=cy+dy-max(y for y,x,c in shape);x=cx+dx-max(x for y,x,c in shape)
    if y%2 or x%2:return None
    return dict(obj,shape=shape,origin=(y//2,x//2))


class Learner:
    def __init__(self):
        self.previous=None;self.models={};self.rows={};self.trials=Counter()
        self.pending=None;self.failed=set();self.steps=0;self.templates={}

    def scene(self,frame):
        # A remembered object exists here only if every colored pixel is visible
        # in a unique pose. Partial/ambiguous templates remain unknown.
        f=np.asarray(frame);known=[]
        for signature,body in self.templates.values():
            lab,_=ndimage.label(f==body);matches={}
            for box in ndimage.find_objects(lab):
                if box is None:continue
                for turn in range(4):
                    shape=rotate(signature,turn)
                    by=min(y for y,x,c in shape if c==body);bx=min(x for y,x,c in shape if c==body)
                    y0=box[0].start-by;x0=box[1].start-bx
                    if all(0<=y0+y<len(f) and 0<=x0+x<f.shape[1] and f[y0+y,x0+x]==c for y,x,c in shape):
                        matches[shape,(y0,x0)]=dict(shape=shape,origin=(y0,x0),body=body)
            if len(matches)==1:known.append(next(iter(matches.values())))
        covered={(y+o['origin'][0],x+o['origin'][1]) for o in known for y,x,c in o['shape']}
        for o in objects(frame):
            cells={(y+o['origin'][0],x+o['origin'][1]) for y,x,c in o['shape']}
            familiar_body=any(body==o['body'] for signature,body in self.templates.values())
            if not cells&covered and not familiar_body:known.append(o)
        return sorted(known,key=lambda o:(o['origin'],o['shape']))

    def observe(self,raw,action=None):
        obs=public(raw);old=self.previous;intent=self.pending;self.pending=None
        if old is not None:
            progress=obs['levels_completed']!=old['levels_completed'] or obs['state']=='WIN'
            if progress:
                self.models={};self.rows={};self.trials.clear();self.failed.clear();self.templates={}
            elif action in (1,2,3,4,5,7) and old['state']==obs['state']=='NOT_FINISHED':
                left=defaultdict(list);right=defaultdict(list)
                for o in self.scene(old['frame']):left[identity(o)].append(o)
                for o in self.scene(obs['frame']):right[identity(o)].append(o)
                h=digest(dict(before=old,action=action,after=obs))
                self.rows[h]=dict(before=old,action=action,after=obs)
                for key in left.keys()&right.keys():
                    if len(left[key])!=1 or len(right[key])!=1:continue
                    a,b=left[key][0],right[key][0];ca,cb=center2(a),center2(b)
                    rules={(t,cb[0]-ca[0],cb[1]-ca[1]) for t in range(4) if rotate(a['shape'],t)==b['shape']}
                    m=self.models.setdefault((key,action),dict(rules=None,origins=set(),support=[],changed=False))
                    m['rules']=rules if m['rules'] is None else m['rules']&rules
                    m['origins'].add((a['shape'],a['origin']));m['support'].append(h);m['changed']|=a!=b
                    if intent and intent['actor_identity']==key and b['shape']==intent['goal']['shape'] and b['origin']==intent['goal']['origin']:
                        self.failed.add((key,b['shape'],b['origin']))
                # Unknown merged/occluded identities are not a failed goal trial.
            if action is not None:self.trials[action]+=1;self.steps+=1
        if obs['state']=='NOT_FINISHED':
            for o in self.scene(obs['frame']):self.templates[identity(o)]=(o['shape'],o['body'])
        self.previous=copy.deepcopy(obs)

    def model(self,obj,action):
        m=self.models.get((identity(obj),action))
        if not m or len(m['origins'])<2 or not m['rules']:return None
        predictions=[apply(obj,r) for r in sorted(m['rules'])]
        if any(p is None for p in predictions) or any(p!=predictions[0] for p in predictions):return None
        return predictions[0],m

    def propose(self,obs):
        if obs['state']!='NOT_FINISHED':return None
        legal=sorted(set(obs['available_actions'])&{1,2,3,4,5,7});scene=self.scene(obs['frame']);plans=[]
        for actor in scene:
            if not any(k==identity(actor) and m['changed'] and m['rules'] for (k,a),m in self.models.items()):continue
            for goal in hypotheses(actor,scene):
                if (identity(actor),goal['shape'],goal['origin']) in self.failed:continue
                def heuristic(p):
                    return abs(p['origin'][0]-goal['origin'][0])+abs(p['origin'][1]-goal['origin'][1])+int(p['shape']!=goal['shape'])*4
                queue=[(heuristic(actor),0,0,actor,[])];seen=set();serial=0
                while queue and len(seen)<512:
                    _,depth,_,here,path=heapq.heappop(queue);key=(here['shape'],here['origin'])
                    if key in seen:continue
                    seen.add(key)
                    if key==(goal['shape'],goal['origin']):
                        if path:plans.append((len(path),heuristic(actor),actor,goal,path))
                        break
                    if depth>=80:continue
                    for action in legal:
                        model=self.model(here,action)
                        if model is None:continue
                        predicted,m=model
                        if predicted==here:continue
                        if any(not(0<y+predicted['origin'][0]<len(obs['frame'])-1 and 0<x+predicted['origin'][1]<len(obs['frame'][0])-1) for y,x,c in predicted['shape']):continue
                        cells={(y+predicted['origin'][0],x+predicted['origin'][1]) for y,x,c in predicted['shape']}
                        occupied={(y+q['origin'][0],x+q['origin'][1]) for q in scene if identity(q)!=identity(actor) for y,x,c in q['shape']}
                        terminal=(predicted['shape'],predicted['origin'])==(goal['shape'],goal['origin'])
                        if cells&occupied:continue
                        if not terminal and any((y+dy,x+dx) in occupied for y,x in cells for dy,dx in ((1,0),(-1,0),(0,1),(0,-1))):continue
                        serial+=1;edge=dict(action=action,predicted=predicted,rules=sorted(m['rules']),support=sorted(set(m['support'])))
                        heapq.heappush(queue,(depth+1+heuristic(predicted),depth+1,serial,predicted,path+[edge]))
        if not plans:return None
        _,_,actor,goal,path=min(plans,key=lambda p:(p[0],p[1],p[2]['origin'],p[3]['origin']))
        return dict(action=path[0]['action'],data={},kind='composite_connector_plan',actor=actor,actor_identity=identity(actor),
                    goal=goal,path=path,context=digest(obs))

    def commit(self,cert):
        self.pending=copy.deepcopy(cert)

    def choose(self,obs):
        if obs['state']=='WIN':return None
        if obs['state'] in ('GAME_OVER','NOT_PLAYED'):return 0
        cert=self.propose(obs)
        if cert:self.commit(cert);return cert['action']
        legal=sorted(set(obs['available_actions'])&{1,2,3,4,5,7})
        return min(legal,key=lambda a:(self.trials[a],a)) if legal else 0
