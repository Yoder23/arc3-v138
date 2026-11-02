"""Learn coupled controls and test a visual convergence goal using legal observations."""
from collections import Counter,deque
import copy,itertools
from structured_interaction_probe_v1 import parts
from visual_transform_learner import digest

def actors(frame,signature=None):
    groups={}
    for o in parts(frame):
        if o['y']<=0 or o['h']!=o['w'] or o['area']!=o['h']*o['w'] or not(2<=o['h']<=8):continue
        key=(o['color'],o['h']);groups.setdefault(key,[]).append(o)
    if signature is None:
        candidates=[(k,v) for k,v in groups.items() if len(v)==2]
        if len(candidates)!=1:return None,None
        signature=candidates[0][0]
    objects=groups.get(signature,[])
    if len(objects)!=2:
        color,size=signature;unseen={(y,x) for y,row in enumerate(frame) for x,v in enumerate(row) if v==color and 0<y<63 and 0<x<63}
        if len(unseen)!=2*size*size:return signature,None
        first=min(unseen);tile={(first[0]+a,first[1]+b) for a in range(size) for b in range(size)}
        if not tile<=unseen:return signature,None
        remaining=unseen-tile;second=min(remaining)
        if remaining!={(second[0]+a,second[1]+b) for a in range(size) for b in range(size)}:return signature,None
        return signature,tuple(sorted((first,second),key=lambda p:(p[1],p[0])))
    return signature,tuple((o['y'],o['x']) for o in sorted(objects,key=lambda o:(o['x'],o['y'])))

def cells(pos,size):return {(y+a,x+b) for y,x in pos for a in range(size) for b in range(size)}
def board(obs,pos,size,floor):
    f=copy.deepcopy(obs['frame'])
    for y,x in cells(pos,size):f[y][x]=floor
    return f

def landmarks(obs,floor,size,hazards,actor_color=None):
    found=[];f=obs['frame'];totals=Counter(v for row in f for v in row)
    for q in parts(f):
        if totals[q['color']]>2*size*size or q['color']==floor or q['color'] in hazards or not(1<=q['area']<=((size+1)//2)**2):continue
        pixels={(q['y']+int(y),q['x']+int(x)) for y,x in q['shape']};ring={p for y,x in pixels for p in ((y-1,x),(y+1,x),(y,x-1),(y,x+1))}-pixels
        if not ring or not all(0<=y<64 and 0<=x<64 and f[y][x] in (floor,actor_color) for y,x in ring):continue
        found.append(dict(color=q['color'],pixels=sorted(pixels),interpretation='embedded_compact_landmark'))
    return found

def predict(f,pos,size,effects,floor,hazards=()):
    out=[]
    for (y,x),(dy,dx) in zip(pos,effects):
        ny,nx=y+dy,x+dx
        if any(f[ny+a][nx+b] in hazards for a in range(size) for b in range(size) if 0<=ny+a<64 and 0<=nx+b<64):return None
        good=all(0<ny+a<63 and 0<nx+b<63 and f[ny+a][nx+b]==floor for a in range(size) for b in range(size))
        out.append((ny,nx) if good else (y,x))
    return tuple(out)
class Agent:
    def __init__(self):
        self.level=None;self.signature=None;self.previous=None;self.previous_pos=None;self.last=None;self.models={};self.history={};self.floor_counts=Counter();self.floor_sources=[];self.trials=Counter();self.visits=Counter();self.blocked={};self.predicted=None;self.goal_memory=[];self.archive=[];self.spawn_pos=None;self.spawn_source=None;self.hazards={};self.failures=[];self.identity_ambiguous=False;self.last_data={};self.interaction_queue=[];self.interaction_tests=set();self.interaction_outcomes=[]
    def observe(self,obs,pos):
        if self.previous is None or self.last is None:return
        row=dict(before=self.previous,action=self.last,data=copy.deepcopy(self.last_data),after=copy.deepcopy(obs));source=digest(row);self.history[source]=row
        if self.last==0:return
        if self.last in (5,6):self.interaction_outcomes.append(dict(source=source,action=self.last,changed_pixels=sum(a!=b for x,y in zip(self.previous['frame'][1:63],obs['frame'][1:63]) for a,b in zip(x,y)),progress=obs['levels_completed']>self.previous['levels_completed']))
        if obs['levels_completed']>self.previous['levels_completed'] or obs['state']=='WIN':self.goal_memory.append(dict(source=source,hypothesis='coincident_actors',progress=True));return
        if pos is None or self.previous_pos is None or self.previous['levels_completed']!=obs['levels_completed']:return
        size=self.signature[1];col=self.signature[0];effects,_=self.controls();motion=effects.get(self.last)
        if motion and self.spawn_pos==pos and self.previous_pos!=pos and any(abs(b[0]-a[0])+abs(b[1]-a[1])>abs(dy)+abs(dx) for a,b,(dy,dx) in zip(self.previous_pos,pos,motion)):
            self.failures.append(source);self.blocked[(self.previous_pos,self.last)]=source
            if self.floor_counts:
                floor=self.floor_counts.most_common(1)[0][0]
                for index,((y,x),(dy,dx)) in enumerate(zip(self.previous_pos,motion)):
                    ny,nx=y+dy,x+dx;values={self.previous['frame'][ny+a][nx+b] for a in range(size) for b in range(size) if 0<=ny+a<64 and 0<=nx+b<64};other=values-{floor,col}
                    if floor in values and len(other)==1:
                        color=next(iter(other));self.hazards[color]=dict(source=source,actor=index,before_positions=self.previous_pos,attempted=(ny,nx),spawn=self.spawn_pos,spawn_source=self.spawn_source,color=color,interpretation='mixed_surface_failure_return')
            return
        if motion and self.floor_counts and self.last in (1,2,3,4,7):
            floor=self.floor_counts.most_common(1)[0][0]
            for i,((y,x),(dy,dx)) in enumerate(zip(self.previous_pos,motion)):
                if pos[i]!=self.previous_pos[i] or (dy,dx)==(0,0):continue
                destination={(y+dy+a,x+dx+b) for a in range(size) for b in range(size)}
                for marker in landmarks(self.previous,floor,size,self.hazards,self.signature[0]):
                    pixels=set(map(tuple,marker['pixels']))
                    if not destination&pixels:continue
                    identity=(self.level,marker['color'],tuple(sorted(pixels)))
                    if identity in self.interaction_tests:continue
                    self.interaction_tests.add(identity);cy,cx=min(pixels)
                    for probe,data in ((5,{}),(6,dict(x=cx,y=cy))):
                        if probe in obs['available_actions']:self.interaction_queue.append(dict(action=probe,data=data,marker=marker,source=source))
        departed=cells(self.previous_pos,size)-cells(pos,size)
        found=Counter(obs['frame'][y][x] for y,x in departed if self.previous['frame'][y][x]==col)
        if found:self.floor_counts.update(found);self.floor_sources.append(source)
        if self.identity_ambiguous or self.last==6:return
        for i,(a,b) in enumerate(zip(self.previous_pos,pos)):
            delta=b[0]-a[0],b[1]-a[1]
            if delta==(0,0):continue
            m=self.models.setdefault(self.last,[{},{}])[i];record=m.setdefault(delta,dict(support=[],origins=set()));record['support'].append(dict(source=source,before=a,after=b,actor=i));record['origins'].add(a)
        if self.predicted is not None and self.predicted!=pos:self.blocked[(self.previous_pos,self.last)]=source
    def controls(self):
        out={};proof={}
        for action,ms in self.models.items():
            chosen=[]
            for m in ms:
                eligible=[(k,v) for k,v in m.items() if len(v['origins'])>=2]
                if len(eligible)!=1:break
                chosen.append(eligible[0])
            if len(chosen)==2:out[action]=tuple(k for k,v in chosen);proof[action]=[v['support'] for k,v in chosen]
        return out,proof
    def plan(self,obs,pos):
        if not self.floor_counts:return None,None
        floor=self.floor_counts.most_common(1)[0][0];size=self.signature[1];f=board(obs,pos,size,floor);hypotheses=landmarks(obs,floor,size,self.hazards,self.signature[0])
        for q in hypotheses:
            for y,x in q['pixels']:f[y][x]=floor
        controls,proof=self.controls();queue=deque([(pos,[])]);seen={pos}
        while queue and len(seen)<25000:
            here,path=queue.popleft()
            if here[0]==here[1] and path:return path,dict(floor=floor,effects=controls,support=proof,expanded=len(seen),landmark_hypotheses=hypotheses)
            for action,effects in sorted(controls.items()):
                if (here,action) in self.blocked:continue
                after=predict(f,here,size,effects,floor,self.hazards)
                if after is None or after in seen:continue
                seen.add(after);queue.append((after,path+[(action,after)]))
        return None,dict(floor=floor,effects=controls,support=proof,expanded=len(seen),landmark_hypotheses=hypotheses)
    def respond(self,obs):
        signature,pos=actors(obs['frame'],self.signature if self.level==obs['levels_completed'] else None)
        self.identity_ambiguous=False
        if pos and self.previous_pos and self.level==obs['levels_completed'] and self.last!=0:
            assignments=sorted((sum(abs(a[0]-b[0])+abs(a[1]-b[1]) for a,b in zip(self.previous_pos,q)),q) for q in itertools.permutations(pos))
            self.identity_ambiguous=len(assignments)>1 and assignments[0][0]==assignments[1][0];pos=assignments[0][1]
            if self.spawn_pos and set(pos)==set(self.spawn_pos):pos=self.spawn_pos
        self.observe(obs,pos)
        if obs['state'] in ('WIN','GAME_OVER'):
            self.previous=copy.deepcopy(obs);self.previous_pos=None;self.last=None if obs['state']=='WIN' else 0;self.last_data={};self.predicted=None
            return dict(action=None if obs['state']=='WIN' else 0,data={},done=obs['state']=='WIN',certificate=None,advisor='coupled_navigation',diagnostics=dict(reason=obs['state'],retained=len(self.history)))
        if self.level!=obs['levels_completed']:
            self.archive.append(dict(level=self.level,models=copy.deepcopy(self.models),blocked=copy.deepcopy(self.blocked)));self.level=obs['levels_completed'];self.signature=signature;self.models={};self.floor_counts=Counter();self.floor_sources=[];self.trials=Counter();self.visits=Counter();self.blocked={};self.spawn_pos=pos;self.spawn_source=digest(obs);self.hazards={};self.interaction_queue=[]
        legal=sorted(set(obs['available_actions'])&{1,2,3,4,5,7});cert=None;path=None;self.predicted=None;info=None;data={};inquiry=None
        while self.interaction_queue:
            candidate=self.interaction_queue.pop(0);marker=candidate['marker']
            if all(obs['frame'][y][x]==marker['color'] for y,x in marker['pixels']):inquiry=candidate;break
        if not inquiry and pos and sum(self.trials.values())>=12:path,info=self.plan(obs,pos)
        if inquiry:
            action=inquiry['action'];data=inquiry['data'];reason='test_interaction_after_blocked_landmark'
        elif path:
            action=path[0][0];self.predicted=path[0][1];reason='coupled_convergence_plan';cert=dict(kind='coupled_motion_plan',tracking_is_hypothesis=True,context=digest(obs),signature=self.signature,positions=pos,action=action,path=[dict(action=a,positions=p) for a,p in path],hypothesis='coincident_actors',floor_is_hypothesis=True,floor_sources=self.floor_sources,retained_goal_memory=self.goal_memory,hazard_hypotheses=list(self.hazards.values()),**info)
        else:
            action=min(legal,key=lambda a:(self.visits[(pos,a)],self.trials[a],a)) if legal else None;reason='identify_coupled_controls' if pos else 'actors_unresolved'
        self.previous=copy.deepcopy(obs);self.previous_pos=pos;self.last=action;self.last_data=copy.deepcopy(data);self.trials[action]+=1;self.visits[(pos,action)]+=1
        return dict(action=action,data=data,done=action is None,certificate=cert,advisor='coupled_navigation',diagnostics=dict(reason=reason,retained=len(self.history),supported_controls=len(self.controls()[0]),failed_predictions=len(self.blocked),goal_success_memories=len(self.goal_memory),expanded=info['expanded'] if info else 0,hazard_hypotheses=len(self.hazards),failure_returns=len(self.failures),interaction_contexts=len(self.interaction_tests),interaction_outcomes=len(self.interaction_outcomes)))
