"""Learn directional encounter dynamics and plan intermediate evasive movements."""
import copy,heapq
from collections import Counter
from binary_demonstration_bootstrap_v1 import components
from pursuit_motion_v1 import advance as pursuit_advance
DIRS={1:(-1,0),2:(1,0),3:(0,-1),4:(0,1)}
def perception(frame,identity=None):
    obs=components(frame);outside=Counter(v for row in frame[:-1]for v in row).most_common(1)[0][0];bodies=[]
    for o in obs:
        y,x,n,w=o['box']
        if not 3<=n==w<=7 or n%2==0 or len(o['shape'])!=n*n-1:continue
        missing=next((dy,dx)for dy in range(n)for dx in range(n)if(dy,dx)not in o['shape']);dy,dx=missing[0]-n//2,missing[1]-n//2
        if (dy==0)==(dx==0)or abs(dy)+abs(dx)!=n//2:continue
        bodies.append(dict(object=o,ink=o['ink'],position=(y,x),heading=(0 if dy==0 else 1 if dy>0 else -1,0 if dx==0 else 1 if dx>0 else -1)))
    candidates=[b for b in bodies if identity is None or b['ink']==identity]
    if len(candidates)!=1:return None
    actor=candidates[0];y,x=actor['position'];n=actor['object']['box'][2];stride=2*n;enemies=sorted((b for b in bodies if b!=actor),key=lambda b:(b['ink'],b['heading'],b['position']))
    nodes=set()
    for yy in range(y%stride,64-n+1,stride):
        for xx in range(x%stride,64-n+1,stride):
            if all(frame[a][b]!=outside for a in range(yy,yy+n)for b in range(xx,xx+n)):nodes.add((yy,xx))
    links={}
    for pos in nodes:
        links[pos]={}
        for action,(dy,dx)in DIRS.items():
            q=(pos[0]+dy*stride,pos[1]+dx*stride);mid=(pos[0]+dy*n,pos[1]+dx*n)
            if q in nodes and all(frame[a][b]!=outside for a in range(mid[0],mid[0]+n)for b in range(mid[1],mid[1]+n)):links[pos][action]=q
    colors=Counter(o['ink']for o in obs if o['box'][2:]==(n,n)and len(o['shape'])==n*n)
    goals=[o for o in obs if o['box'][2:]==(n,n)and len(o['shape'])==n*n and colors[o['ink']]==1 and o['ink']!=outside and o['box'][:2]in nodes]
    if len(goals)>1:return None
    return dict(actor=actor,enemies=enemies,goal=goals[0]if goals else None,outside=outside,stride=stride,links=links)
def enemies(frame,identity,n):
    result=[]
    for o in components(frame):
        if o['ink']==identity or o['box'][2:]!=(n,n)or len(o['shape'])!=n*n-1:continue
        missing=next((dy,dx)for dy in range(n)for dx in range(n)if(dy,dx)not in o['shape']);dy,dx=missing[0]-n//2,missing[1]-n//2
        if (dy==0)==(dx==0)or abs(dy)+abs(dx)!=n//2:continue
        result.append((o['ink'],(0 if dy==0 else 1 if dy>0 else -1,0 if dx==0 else 1 if dx>0 else -1),o['box'][:2]))
    return sorted(result)
def advance_enemies(actor,old,links,stride,radius,old_actor=None,active=()):
    out=[]
    for ink,heading,pos in old:
        rule=radius.get(ink,0)if isinstance(radius,dict)else radius
        if rule>=19:
            heading,pos=pursuit_advance(old_actor or actor,heading,pos,links,stride,rule-18,ink in active)
            out.append((ink,heading,pos));continue
        if rule in (17,18):
            action=next(a for a,d in DIRS.items()if d==heading)
            pos=links.get(pos,{}).get(action,pos)
            if rule==17 and action not in links.get(pos,{}):heading=tuple(-v for v in heading)
            out.append((ink,heading,pos));continue
        dy,dx=heading;delta=(actor[0]-pos[0],actor[1]-pos[1]);distance=delta[0]*dy+delta[1]*dx
        aligned=(dy==0 and delta[0]==0)or(dx==0 and delta[1]==0);steps=distance//stride
        action=next(a for a,d in DIRS.items()if d==heading);at=pos;clear=True
        if aligned and distance>0 and distance%stride==0 and steps<=rule:
            for _ in range(steps):
                at=links.get(at,{}).get(action)
                if at is None:clear=False;break
            if clear:pos=links.get(pos,{}).get(action,pos)
        out.append((ink,heading,pos))
    return tuple(sorted(out))
def search(s,radius,blocked,limit=40000,capture=False,active=()):
    if s['goal']is None:return None
    start=(s['actor']['position'],tuple((b['ink'],b['heading'],b['position'])for b in s['enemies']),tuple(sorted(active)));target=s['goal']['box'][:2];step=s['stride'];links=s['links']
    queue=[(0,0,start,[])];best={start:0};n=0
    while queue and n<limit:
        _,cost,state,path=heapq.heappop(queue);n+=1
        if state[0]==target:return path
        if cost!=best[state]or cost>=100:continue
        for a,q in sorted(links.get(state[0],{}).items()):
            if (state[:2],a)in blocked or (not capture and q in [e[2]for e in state[1]]):continue
            remaining=tuple(e for e in state[1]if not capture or e[2]!=q or (isinstance(radius,dict)and radius.get(e[0],0)>=17))
            moved=advance_enemies(q,remaining,links,step,radius,old_actor=state[0],active=state[2])
            if q in [e[2]for e in moved]:continue
            activated=tuple(sorted(set(state[2])|{b[0]for b,a in zip(remaining,moved)if b[0]==a[0]and b[2]!=a[2]}));after=(q,moved,activated)
            if cost+1>=best.get(after,10**9):continue
            best[after]=cost+1;h=(abs(q[0]-target[0])+abs(q[1]-target[1]))/step
            heapq.heappush(queue,(cost+1+h,cost+1,after,path+[(a,after)]))
    return None
class Agent:
    def __init__(self,prior=None):
        self.prior=prior;self.active=True;self.identity=None;self.previous=None;self.t=0;self.level=None;self.evidence=[];self.failures=[];self.archive=[];self.rules=set(range(0,17));self.plan=[];self.expected=None;self.blocked=set();self.visits=Counter();self.restarts=0;self.contact_evidence=[];self.role_rules={};self.role_evidence=[];self.pursuit_active=set();self.activation_evidence=[]
    def respond(self,raw):
        s=perception(raw['frame'],self.identity)
        if self.previous and self.previous['raw']['state']=='NOT_FINISHED'and self.previous['raw']['levels_completed']==raw['levels_completed']:
            p=self.previous;before=p['scene'];old=tuple((b['ink'],b['heading'],b['position'])for b in before['enemies']);after=tuple(enemies(raw['frame'],self.identity,before['actor']['object']['box'][2]));actual=s['actor']['position']if s else None
            q=before['links'].get(before['actor']['position'],{}).get(p['action'],before['actor']['position'])
            predictions={r:advance_enemies(q,old,before['links'],before['stride'],r)for r in range(0,17)}
            valid={r for r,v in predictions.items()if v==after};same=len(old)==len(after)
            for ink in sorted({v[0]for v in old}):
                b=tuple(v for v in old if v[0]==ink);a=tuple(v for v in after if v[0]==ink)
                if len(a)!=len(b):continue
                supported={i for i in range(23)if advance_enemies(q,b,before['links'],before['stride'],i,old_actor=before['actor']['position'],active=self.pursuit_active)==a}
                previous=self.role_rules.get(ink,set(range(23)));remaining=previous&supported
                if supported:self.role_rules[ink]=remaining or supported
                self.role_evidence.append(dict(source=p['source'],ink=ink,before=b,after=a,matching=sorted(supported),previous=sorted(previous),retained=sorted(self.role_rules.get(ink,previous)),active_before=sorted(self.pursuit_active)))
            if same and old:
                remaining=self.rules&valid
                if remaining:self.rules=remaining
                elif valid:self.failures.append(dict(source=p['source'],kind='enemy_rule_revised',old=sorted(self.rules),new=sorted(valid)));self.rules=valid
            if actual is not None and len(after)==len(old)-1 and any(v[2]==actual for v in old)and tuple(v for v in old if v[2]!=actual)==after:
                self.contact_evidence.append(dict(source=p['source'],position=actual,before=old,after=after))
            for ink in {v[0]for v in old}:
                b=[v for v in old if v[0]==ink];a=[v for v in after if v[0]==ink]
                if len(a)==len(b)and any(v[2]!=w[2]for v,w in zip(b,a)):
                    self.pursuit_active.add(ink);self.activation_evidence.append(dict(source=p['source'],ink=ink))
            record=dict(source=p['source'],action=p['action'],before=before['actor']['position'],after=actual,enemies_before=old,enemies_after=after,matching_rules=sorted(valid),state=raw['state'])
            self.evidence.append(record)
            if raw['state']=='GAME_OVER':
                self.blocked.add(((before['actor']['position'],old),p['action']));self.failures.append(dict(source=p['source'],kind='terminal_encounter',position=before['actor']['position'],action=p['action']));self.plan=[]
            elif self.expected is not None and (actual,after,tuple(sorted(self.pursuit_active)))!=self.expected:self.plan=[];self.failures.append(dict(source=p['source'],kind='prediction_mismatch',expected=self.expected,actual=(actual,after,tuple(sorted(self.pursuit_active)))))
        self.previous=None
        if raw['state']=='GAME_OVER':
            if self.restarts>=8:return dict(done=True,action=None,data={})
            self.restarts+=1;self.plan=[];self.expected=None;self.pursuit_active=set()
            c=dict(kind='directional_encounter',source=self.t,tag='retry_retaining_failed_encounters',scene=None,evidence=copy.deepcopy(self.evidence),failures=copy.deepcopy(self.failures),rules=sorted(self.rules),activation_evidence=copy.deepcopy(self.activation_evidence),active_roles=sorted(self.pursuit_active),role_evidence=copy.deepcopy(self.role_evidence),role_rules={k:sorted(v)for k,v in self.role_rules.items()},archive=copy.deepcopy(self.archive))
            self.t+=1;return dict(done=False,action=0,data={},certificate=c)
        if raw['state']!='NOT_FINISHED'or s is None:return dict(done=True,action=None,data={})
        if self.identity is None:self.identity=s['actor']['ink']
        if self.level!=raw['levels_completed']:
            if self.level is not None:self.archive.append(dict(level=self.level,evidence_count=len(self.evidence),failures_count=len(self.failures)))
            self.level=raw['levels_completed'];self.plan=[];self.expected=None;self.blocked=set();self.visits=Counter();self.restarts=0;self.pursuit_active=set()
        radius={ink:(min(rules)if min(rules)>=17 else 0 if 0 in rules else max(r for r in rules if r<17))for ink,rules in self.role_rules.items()};state=(s['actor']['position'],tuple((b['ink'],b['heading'],b['position'])for b in s['enemies']),tuple(sorted(self.pursuit_active)))
        if not self.plan:self.plan=search(s,radius,self.blocked,capture=bool(self.contact_evidence),active=self.pursuit_active)or search(s,radius,self.blocked,capture=True,active=self.pursuit_active)or[]
        if self.plan:action,self.expected=self.plan.pop(0);tag='compose_navigation_and_observed_encounters'
        else:
            options=[]
            for a,q in s['links'].get(state[0],{}).items():
                moved=advance_enemies(q,state[1],s['links'],s['stride'],radius,old_actor=state[0],active=self.pursuit_active)
                if (state[:2],a)not in self.blocked and q not in [v[2]for v in moved]:options.append((self.visits[(state,a)],a))
            if not options or self.t>=512:return dict(done=True,action=None,data={})
            action=min(options)[1];self.expected=None;tag='test_alternative_encounter_context'
        self.visits[(state,action)]+=1
        c=dict(kind='directional_encounter',source=self.t,tag=tag,scene={k:v for k,v in s.items()if k!='links'},evidence=copy.deepcopy(self.evidence),failures=copy.deepcopy(self.failures),rules=sorted(self.rules),radius_hypothesis=radius,activation_evidence=copy.deepcopy(self.activation_evidence),active_roles=sorted(self.pursuit_active),role_evidence=copy.deepcopy(self.role_evidence),role_rules={k:sorted(v)for k,v in self.role_rules.items()},contact_evidence=copy.deepcopy(self.contact_evidence),contact_role_is_hypothesis=not bool(self.contact_evidence),archive=copy.deepcopy(self.archive),prediction=self.expected)
        self.previous=dict(raw=copy.deepcopy(raw),scene=s,action=action,source=self.t);self.t+=1
        return dict(done=False,action=action,data={},certificate=c)
