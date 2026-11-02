"""Test splitter hypotheses, retain fire outcomes and compose moves of several bars."""
import copy,itertools,hashlib,json
from collections import deque
from beam_split_geometry_v5 import perceive,trace,plan,overlap
from beam_motion_constraints_v1 import infer,allowed
from beam_coupled_motion_v1 import infer as infer_groups
DIRS={1:(-1,0),2:(1,0),3:(0,-1),4:(0,1)}
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def align(s,old):
    if len(s['bars'])!=len(old['bars']):return s
    best=None
    for order in itertools.permutations(range(len(s['bars']))):
        if any(old['bars'][i]['box'][2:]!=s['bars'][j]['box'][2:]for i,j in enumerate(order)):continue
        cost=sum(abs(a-b)for i,j in enumerate(order)for a,b in zip(old['bars'][i]['box'][:2],s['bars'][j]['box'][:2]))
        if best is None or(cost,order)<best:best=(cost,order)
    if best:s=dict(s,bars=[s['bars'][j]for j in best[1]])
    return s
def move_route(s,index,target,blocked,groups=None):
    group=next((g for g in(groups or[])if index in g),(index,))
    n=s['n'];box=s['bars'][index]['box'];start=box[:2];queue=deque([(start,[])]);seen={start}
    obstacles=[b['box']for i,b in enumerate(s['bars'])if i not in group]+[g['object']['box']for g in s['goals']]+[z[k]['box']for z in s['sources']for k in ('object','companion')]
    while queue:
        p,path=queue.popleft()
        if p==target:return path
        for a,(dy,dx)in DIRS.items():
            q=p[0]+dy*n,p[1]+dx*n;dest=(*q,*box[2:])
            if q in seen or(p,a)in blocked or not((s['origin'][0]or n)<=q[0]<=64-box[2]and s['origin'][1]<=q[1]<=64-box[3])or any(overlap((q[0]+s['bars'][j]['box'][0]-start[0],q[1]+s['bars'][j]['box'][1]-start[1],*s['bars'][j]['box'][2:]),b)for j in group for b in obstacles):continue
            seen.add(q);queue.append((q,path+[a]))
    return None
class Agent:
    def __init__(self,prior=None):
        self.prior=prior;self.active=True;self.level=None;self.t=0;self.previous=None;self.last_scene=None;self.selection_ink=None;self.target=None;self.failed=set();self.blocked={};self.evidence=[];self.fire_evidence=[];self.failures=[];self.archive=[];self.restarts=0;self.level_failure_start=0;self.motion_limits={};self.groups=[];self.group_sources=[];self.level_evidence_start=0
    def respond(self,raw):
        s=perceive(raw['frame'])
        if s and self.last_scene and raw['levels_completed']==self.level:s=align(s,self.last_scene)
        if self.previous:
            p=self.previous;old=p['scene'];same=raw['levels_completed']==self.level
            if p['action']==5:
                predicted=trace(old,tuple(b['box'][:2]for b in old['bars']));color=old['source']['object']['ink'];n=old['n'];tiles=set()
                for f in raw['animation_frames']:
                    for y in range(old['origin'][0],64,n):
                        for x in range(old['origin'][1],64,n):
                            if all(f[yy][xx]==color for yy in range(y,min(y+n,64))for xx in range(x,min(x+n,64))):tiles.add((y,x))
                r=dict(source=p['source'],configuration=tuple(b['box'][:2]for b in old['bars']),prediction=predicted,observed_beam_tiles=sorted(tiles),after_digest=digest(raw),completed=raw['levels_completed']>self.level)
                self.fire_evidence.append(r)
                if same:self.failed.add(r['configuration']);self.failures.append(dict(source=p['source'],kind='goal_attempt_failed',configuration=r['configuration'],predicted_hits=predicted['hits']));self.target=None
            elif same and s:
                before=tuple(b['box'][:2]for b in old['bars']);after=tuple(b['box'][:2]for b in s['bars']);r=dict(source=p['source'],action=p['action'],data=p['data'],before=before,after=after,colors_before=[b['ink']for b in old['bars']],colors_after=[b['ink']for b in s['bars']]);self.evidence.append(r)
                if p['action']in DIRS and before==after:
                    context=tuple(v for i,v in enumerate(before)if i!=p['index']);self.blocked.setdefault((p['index'],context),set()).add((before[p['index']],p['action']));self.failures.append(dict(source=p['source'],kind='bar_motion_blocked',index=p['index'],position=before[p['index']],action=p['action'],context=context))
                if p['action']==6 and s['bars'][p['index']]['ink']!=old['bars'][p['index']]['ink']:self.selection_ink=s['bars'][p['index']]['ink']
        self.previous=None
        if raw['state']=='GAME_OVER':
            if self.restarts>=4:return dict(done=True,action=None,data={})
            self.restarts+=1;self.last_scene=None;self.target=None;self.t+=1
            return dict(done=False,action=0,data={},certificate=dict(kind='beam_split',source=self.t-1,tag='retry_retaining_fire_failures',scene=None,evidence=copy.deepcopy(self.evidence),fire_evidence=copy.deepcopy(self.fire_evidence),failures=copy.deepcopy(self.failures),archive=copy.deepcopy(self.archive)))
        if raw['state']!='NOT_FINISHED'or s is None:return dict(done=True,action=None,data={})
        if self.level!=raw['levels_completed']:
            if self.level is not None:self.archive.append(dict(level=self.level,evidence_count=len(self.evidence),fire_count=len(self.fire_evidence),failures_count=len(self.failures)))
            self.level=raw['levels_completed'];self.target=None;self.failed=set();self.blocked={};self.last_scene=None;self.level_failure_start=len(self.failures);self.motion_limits={};self.level_evidence_start=len(self.evidence);self.groups=[];self.group_sources=[]
        if len(s['bars'])==1:self.selection_ink=s['bars'][0]['ink']
        groups,sources=infer_groups(self.evidence[self.level_evidence_start:],len(s['bars']))
        if groups!=self.groups:self.target=None
        self.groups=groups;self.group_sources=sources
        self.motion_limits=infer(self.failures[self.level_failure_start:])
        if self.target is not None and any(not allowed(i,p,self.motion_limits)for i,p in enumerate(self.target)):self.target=None
        poses=tuple(b['box'][:2]for b in s['bars']);action=None;data={};index=None;tag='test_unmodified_beam_outcome'
        if not self.fire_evidence:action=5
        else:
            if self.target is None:self.target=plan(s,self.failed,limits=self.motion_limits,groups=self.groups)
            if self.target is None:return dict(done=True,action=None,data={})
            if poses==self.target:action=5;tag='test_composed_splitter_configuration'
            else:
                for i,target in enumerate(self.target):
                    if poses[i]==target:continue
                    context=tuple(v for j,v in enumerate(poses)if j!=i);route=move_route(s,i,target,self.blocked.get((i,context),set()),self.groups)
                    if not route:continue
                    index=i;bar=s['bars'][i]
                    if bar['ink']!=self.selection_ink:action=6;data=dict(x=bar['box'][1]+bar['box'][3]//2,y=bar['box'][0]+bar['box'][2]//2);tag='test_bar_selection'
                    else:action=route[0];tag='compose_observed_bar_motion'
                    break
        if action is None or self.t>=512:return dict(done=True,action=None,data={})
        c=dict(kind='beam_split',source=self.t,tag=tag,scene=s,target=self.target,index=index,selection_ink=self.selection_ink,coupled_groups=self.groups,coupled_sources=self.group_sources,motion_limit_hypotheses=copy.deepcopy(self.motion_limits),evidence=copy.deepcopy(self.evidence),fire_evidence=copy.deepcopy(self.fire_evidence),failures=copy.deepcopy(self.failures),archive=copy.deepcopy(self.archive),split_rule_is_hypothesis=not any(r['completed']for r in self.fire_evidence))
        self.previous=dict(source=self.t,action=action,data=data,index=index,scene=copy.deepcopy(s));self.last_scene=copy.deepcopy(s);self.t+=1
        return dict(done=False,action=action,data=data,certificate=c)
