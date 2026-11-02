"""Test splitter hypotheses, retain fire outcomes and compose moves of several bars."""
import copy,itertools,hashlib,json
from collections import deque
from beam_corner_optics_v3 import compare as compare_corner
from beam_connected_source_goal_v1 import evidence as goal_refutation
from beam_joint_model_selection_v1 import compare as compare_joint
from beam_moving_emitter_v1 import discover as discover_emitters,attach as attach_emitters
from beam_front_collision_v2 import compare as compare_front
from beam_retained_segmentation_v3 import recover
from beam_compound_optics_v2 import compare as compare_optics,candidates as optical_candidates
from beam_split_geometry_v20 import perceive,trace,plan,overlap
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
        self.prior=prior;self.active=True;self.level=None;self.t=0;self.previous=None;self.last_scene=None;self.selection_ink=None;self.target=None;self.failed=set();self.blocked={};self.evidence=[];self.fire_evidence=[];self.failures=[];self.archive=[];self.restarts=0;self.level_failure_start=0;self.motion_limits={};self.groups=[];self.group_sources=[];self.level_evidence_start=0;self.planning_failures=[];self.replanning_depth=0;self.optical_rule=None;self.optical_reviews=[];self.front_rule=None;self.front_reviews=[];self.emitter_rule=None;self.emitter_observations=[];self.front_mode="redirect";self.joint_rule=None;self.joint_reviews=[];self.joint_errors=dict(stop=0,redirect=0);self.connected_goal_rule=None;self.goal_refutations=[];self.corner_reviews=[]
    def respond(self,raw):
        s=perceive(raw['frame'])
        if s and self.last_scene and raw['levels_completed']==self.level:s=align(recover(s,self.last_scene,raw['frame'],self.previous['action']if self.previous else None,self.previous.get('index')if self.previous else None,self.previous.get('groups')if self.previous else None),self.last_scene)
        if self.previous:
            p=self.previous;old=p['scene'];same=raw['levels_completed']==self.level
            if p['action']==5:
                predicted=trace(old,tuple(b['box'][:2]for b in old['bars']));color=old['source']['object']['ink'];n=old['n'];tiles=set()
                for f in raw['animation_frames']:
                    for y in range(old['origin'][0],64,n):
                        for x in range(old['origin'][1],64,n):
                            if all(f[yy][xx]==color for yy in range(y,min(y+n,64))for xx in range(x,min(x+n,64))):tiles.add((y,x))
                corner_review=compare_corner(old,p['frame'],raw)if same else None
                if corner_review:self.corner_reviews.append(dict(corner_review,source=p['source']))
                refutation=goal_refutation(old,dict(frame=p['frame'],levels_completed=self.level),raw)if same else None
                if refutation:
                    refutation=dict(refutation,source=p['source']);self.goal_refutations.append(refutation)
                    if self.connected_goal_rule is None:self.connected_goal_rule=copy.deepcopy(refutation);self.target=None
                joint=compare_joint(old,p.get('groups',[]),p['frame'],raw)if same else None
                if joint:
                    joint=dict(joint,source=p['source']);self.joint_reviews.append(joint)
                    for key,value in joint['errors'].items():self.joint_errors[key]+=len(value)
                    preferred=min(self.joint_errors,key=lambda key:(self.joint_errors[key],key))
                    if self.joint_errors[preferred]<self.joint_errors[self.front_mode]:self.front_mode=preferred;self.joint_rule=copy.deepcopy(joint);self.target=None
                births=discover_emitters(old,p.get('groups',[]),p['frame'],raw)
                if births:
                    proof=dict(source=p['source'],births=births);self.emitter_observations.append(proof)
                    if self.emitter_rule is None:self.emitter_rule=copy.deepcopy(proof);self.target=None
                review=compare_front(old,p['frame'],raw)
                if review:
                    review=dict(review,source=p['source']);self.front_reviews.append(review)
                    if review['adopt']and self.front_rule is None:self.front_rule=copy.deepcopy(review);self.target=None
                review=compare_optics(old,p.get('groups',[]),p['frame'],raw)
                if review:
                    review=dict(review,source=p['source']);self.optical_reviews.append(review)
                    if review['adopt'] and self.optical_rule is None:self.optical_rule=copy.deepcopy(review);self.target=None
                r=dict(source=p['source'],configuration=tuple(b['box'][:2]for b in old['bars']),prediction=predicted,observed_beam_tiles=sorted(tiles),after_digest=digest(raw),completed=raw['levels_completed']>self.level)
                self.fire_evidence.append(r)
                if same:self.failed.add(r['configuration']);self.failures.append(dict(source=p['source'],kind='goal_attempt_failed',configuration=r['configuration'],predicted_hits=predicted['hits']));self.target=None
            elif same and s:
                before=tuple(b['box'][:2]for b in old['bars']);after=tuple(b['box'][:2]for b in s['bars']);r=dict(source=p['source'],action=p['action'],data=p['data'],before=before,after=after,colors_before=[b['ink']for b in old['bars']],colors_after=[b['ink']for b in s['bars']]);self.evidence.append(r)
                if p['action']in DIRS and before==after:
                    context=tuple(v for i,v in enumerate(before)if i!=p['index']);self.blocked.setdefault((p['index'],context),set()).add((before[p['index']],p['action']));self.failures.append(dict(source=p['source'],kind='bar_motion_blocked',index=p['index'],position=before[p['index']],action=p['action'],context=context))
                if p['action']==6 and p['index']<len(s['bars']) and s['bars'][p['index']]['ink']!=old['bars'][p['index']]['ink']:self.selection_ink=s['bars'][p['index']]['ink']
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
        s=dict(s,connected_source_goal=bool(self.connected_goal_rule),front_mode=self.front_mode,moving_emitters=attach_emitters(s,self.groups,raw['frame'],self.emitter_rule),front_collision_rule=bool(self.front_rule),optical_groups=optical_candidates(s,self.groups,raw['frame'])if self.optical_rule else[])
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
                    if action==6 and 'corner_missing'in bar:
                        yy,xx=bar['shape'][0];data=dict(x=bar['box'][1]+xx+1,y=bar['box'][0]+yy+1)
                    if action!=6:action=route[0];tag='compose_observed_bar_motion'
                    break
        if action is None and self.target is not None and self.replanning_depth<3:
            self.planning_failures.append(dict(source=self.t,kind='current_planner_cannot_route_configuration',configuration=self.target,scene=copy.deepcopy(s)))
            self.failed.add(self.target);self.target=None;self.replanning_depth+=1
            result=self.respond(raw);self.replanning_depth-=1;return result
        if action is None or self.t>=512:return dict(done=True,action=None,data={})
        c=dict(corner_reviews=copy.deepcopy(self.corner_reviews),connected_goal_rule=copy.deepcopy(self.connected_goal_rule),goal_refutations=copy.deepcopy(self.goal_refutations),joint_rule=copy.deepcopy(self.joint_rule),joint_reviews=copy.deepcopy(self.joint_reviews),joint_errors=copy.deepcopy(self.joint_errors),emitter_rule=copy.deepcopy(self.emitter_rule),emitter_observations=copy.deepcopy(self.emitter_observations),front_rule=copy.deepcopy(self.front_rule),front_reviews=copy.deepcopy(self.front_reviews),optical_rule=copy.deepcopy(self.optical_rule),optical_reviews=copy.deepcopy(self.optical_reviews),planning_failures=copy.deepcopy(self.planning_failures),kind='beam_split',source=self.t,tag=tag,scene=s,target=self.target,index=index,selection_ink=self.selection_ink,coupled_groups=self.groups,coupled_sources=self.group_sources,motion_limit_hypotheses=copy.deepcopy(self.motion_limits),evidence=copy.deepcopy(self.evidence),fire_evidence=copy.deepcopy(self.fire_evidence),failures=copy.deepcopy(self.failures),archive=copy.deepcopy(self.archive),split_rule_is_hypothesis=not any(r['completed']for r in self.fire_evidence))
        self.previous=dict(source=self.t,action=action,data=data,index=index,scene=copy.deepcopy(s),frame=copy.deepcopy(raw['frame']),groups=copy.deepcopy(self.groups));self.last_scene=copy.deepcopy(s);self.t+=1
        return dict(done=False,action=action,data=data,certificate=c)
