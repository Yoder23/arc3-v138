"""Group relational objects by visible labels, learn their mean, and route selected members."""
import copy,heapq,itertools
import numpy as np
from scipy import ndimage
from collections import Counter
from midpoint_relational_learner_v1 import scene as old_scene
from structured_interaction_probe_v1 import parts
from visual_transform_learner import digest

from group_symbolic_scene_v1 import scene,DISK

def blocked(obs,ends):
    f=obs['frame'];bg=Counter(v for row in f for v in row).most_common(1)[0][0]
    walls=set()
    a=np.asarray(f)
    for color in set(a.ravel())-{bg}:
        lab,_=ndimage.label(a==color)
        for j,box in enumerate(ndimage.find_objects(lab),1):
            if box is not None and (lab[box]==j).sum()>=40 and min(b.stop-b.start for b in box)>=3:walls.add(int(color))
    raw={(y,x) for y,row in enumerate(f[:62]) for x,c in enumerate(row) if c in walls}
    # Full sprite clearance is a testable movement hypothesis.
    return {(y,x) for y in range(64) for x in range(64) if y<3 or y>=61 or x<3 or x>=61 or any((y+a,x+b) in raw for a,b in [(a,b) for a in range(-2,3) for b in range(-2,3)])}

def route(start,goal,bad):
    start,goal=tuple(start),tuple(goal)
    if goal in bad:return None
    q=[(0,0,start)];cost={start:0};parent={}
    while q:
        _,n,p=heapq.heappop(q)
        if p==goal:
            path=[p]
            while p!=start:p=parent[p];path.append(p)
            return path[::-1]
        if n!=cost[p]:continue
        for dy,dx in ((-1,0),(0,-1),(0,1),(1,0)):
            v=(p[0]+dy,p[1]+dx)
            if 0<=v[0]<64 and 0<=v[1]<64 and v not in bad and n+1<cost.get(v,99999):cost[v]=n+1;parent[v]=p;heapq.heappush(q,(n+1+abs(v[0]-goal[0])+abs(v[1]-goal[1]),n+1,v))
    return None

def segment(a,b):
    n=max(abs(a[i]-b[i]) for i in (0,1));return [tuple(round(a[i]+(b[i]-a[i])*t/max(n,1)) for i in (0,1)) for t in range(n+1)]
class Agent:
    def __init__(self):
        self.previous=None;self.last=None;self.history={};self.motion=[];self.swaps=[];self.active_color=None;self.level=None;self.goals={};self.goal_source=None;self.layouts={};self.goal_outcomes=[];self.failed=[];self.tries={};self.staging={};self.visual_cache={};self.tracked=[];self.track_level=None;self.expected_counts={};self.visual_signatures={}
    def extract(self,obs):
        h=digest(obs)
        if h in self.visual_cache:return copy.deepcopy(self.visual_cache[h])
        raw,centers,goals=scene(obs);f=obs['frame'];body=[(dy,dx) for dy in range(-2,3) for dx in range(-2,3) if 0<abs(dy)+abs(dx)<=2];disk=[(dy,dx) for dy in range(-2,3) for dx in range(-2,3) if (dy or dx) and not(abs(dy)==abs(dx)==2)]
        if self.track_level!=obs['levels_completed'] or not self.tracked:
            self.tracked=copy.deepcopy(raw);self.track_level=obs['levels_completed'];self.expected_counts=dict(Counter(o['group'] for o in raw));self.visual_signatures={g['color']:dict(signature=g['marker_signature'],center=g['marker_center'],source=g['signature_source']) for g in goals if 'marker_signature' in g}
        else:
            old=self.tracked;colors=sorted({o['color'] for o in old});click=(self.last['data']['y'],self.last['data']['x']) if self.last and self.last['action']==6 else None;selection=click in {o['point'] for o in old};new=[]
            for obj in old:
                positions=[obj['point']]
                if click and not selection and obj['color']==self.active_color:positions=[click]+positions
                choices=[]
                for pos in dict.fromkeys(positions):
                    y,x=pos
                    if not(2<=y<62 and 2<=x<62):continue
                    for color in colors:
                        support=sum(f[y+a][x+b]==color for a,b in body)
                        if support>=8:choices.append((support,pos,color))
                if choices:
                    support,pos,color=max(choices,key=lambda q:q[0]);new.append(dict(color=color,point=pos,group=obj['group']))
            for obj in raw:
                if obj['group'] in self.expected_counts and sum(o['group']==obj['group'] for o in new)<self.expected_counts[obj['group']] and not any(o['group']==obj['group'] and o['point']==obj['point'] for o in new):new.append(copy.deepcopy(obj))
            if len(new)==len(old):self.tracked=new
            else:
                # Do not claim an unobserved displacement when all candidates lose support.
                self.tracked=new
        groups={o['group'] for o in self.tracked}
        for group in groups:
            members=[o for o in self.tracked if o['group']==group]
            if len(members)!=self.expected_counts.get(group):continue
            mean=tuple(sum(o['point'][i] for o in members)//len(members) for i in (0,1));y,x=mean
            if 2<=y<62 and 2<=x<62 and sum(f[y+a][x+b] in self.visual_signatures.get(group,{}).get('signature',[group]) for a,b in disk)>=12:centers[group]=mean
        value=(copy.deepcopy(self.tracked),centers,goals);self.visual_cache[h]=copy.deepcopy(value);return value
    def observe(self,obs):
        if self.previous is None:return
        e=dict(before=self.previous,action=self.last['action'],data=self.last['data'],after=copy.deepcopy(obs));h=digest(e);self.history[h]=e
        if obs['levels_completed']>self.previous['levels_completed'] or obs['state']=='WIN':self.goal_outcomes.append(dict(source=h,progress=True));return
        if self.last['action']!=6:return
        if obs['state']=='GAME_OVER':self.failed.append(dict(source=h,click=(self.last['data']['y'],self.last['data']['x']),reason='actual_terminal_failure'));return
        before,_,_=self.extract(self.previous);after,centers,_=self.extract(obs);p=(self.last['data']['y'],self.last['data']['x'])
        for group in sorted({o['group'] for o in before}):
            a=[o for o in before if o['group']==group];b=[o for o in after if o['group']==group];old={o['point'] for o in a};new={o['point'] for o in b}
            if len(a)==len(b) and len(old-new)==len(new-old)==1 and p in new-old and group in centers:
                mean=tuple(sum(o['point'][i] for o in b)//len(b) for i in (0,1))
                if mean==centers[group]:
                    moved=next(o for o in b if o['point']==p);self.active_color=moved['color'];self.motion.append(dict(source=h,group=group,count=len(b),before=a,after=b,center=mean,origin=next(iter(old-new)),destination=p,**({'marker_signature':self.visual_signatures[group]} if group in self.visual_signatures else {})));break
        if {o['point'] for o in before}=={o['point'] for o in after}:
            changed=[(a,b) for a in before for b in after if a['point']==b['point'] and a['color']!=b['color']]
            if len(changed)==2:self.swaps.append(dict(source=h,click=p,before=before,after=after))
            else:self.failed.append(dict(source=h,click=p,reason=self.last['certificate']['reason']))
    def respond(self,obs):
        self.observe(obs);ends,centers,goals=self.extract(obs);f=obs['frame']
        if self.level!=obs['levels_completed']:
            self.level=obs['levels_completed'];self.goals={g['color']:g for g in goals};self.goal_source=digest(obs);self.layouts={};self.tries={};self.staging={}
        c=dict(kind='group_centroid_plan',context=digest(obs),action=6,goal_is_hypothesis=True,goal_source=self.goal_source,goals=list(self.goals.values()),motion=copy.deepcopy(self.motion),swaps=copy.deepcopy(self.swaps),goal_outcomes=copy.deepcopy(self.goal_outcomes),failures=copy.deepcopy(self.failed));p=None;action=6;reason='unresolved_group_geometry'
        counts=Counter(o['color'] for o in ends)
        if self.active_color is None and counts:self.active_color=min(counts,key=lambda k:(counts[k],k))
        active=next((o for o in ends if o['color']==self.active_color),None);bad=blocked(obs,ends)
        if obs['state']=='GAME_OVER':action=0;reason='reset_after_actual_failure'
        elif obs['state']=='WIN':action=None;reason='WIN'
        elif active and self.goals:
            unsolved=[g for g in sorted(self.goals) if centers.get(g)!=tuple(self.goals[g]['center'])]
            group=active['group'] if active['group'] in unsolved else next(iter(unsolved),None)
            if group is not None:
                members=[o for o in ends if o['group']==group];protected=[v for k,v in centers.items() if k!=group];g=tuple(self.goals[group]['center']);c.update(group=group,goal=g,members=members,active=active)
                if active['group']!=group:p=members[0]['point'];reason='select_unsolved_group'
                else:
                    at=active['point'];n=len(members);supports=[q for q in self.motion if q['count']==n]
                    obskey=digest(dict(objects=[dict(point=o['point'],group=o['group']) for o in ends],levels_completed=obs['levels_completed']));tried=self.tries.setdefault(obskey,set())
                    if len({tuple(q['origin']) for q in supports})<2:
                        candidates=[(at[0]+dy,at[1]+dx) for dy,dx in [(0,6),(6,0),(0,-6),(-6,0),(0,9),(9,0),(0,-9),(-9,0),(0,12),(12,0),(0,-12),(-12,0),(0,18),(18,0),(0,-18),(-18,0)]]
                        candidates=[q for q in candidates if q not in bad and (at,q) not in tried and all(max(abs(q[i]-o['point'][i]) for i in (0,1))>4 for o in ends) and not set(segment(at,q))&bad]
                        candidates=[q for q in candidates if tuple((sum(o['point'][i] for o in members)-at[i]+q[i])//n for i in (0,1)) not in bad]
                        candidates=[q for q in candidates if all(max(abs((q if o is active else o['point'])[i]-((sum(v['point'][i] for v in members)-at[i]+q[i])//n)) for i in (0,1))>=5 for o in members)]
                        candidates=[q for q in candidates if all(max(abs(q[i]-z[i]) for i in (0,1))>=5 for z in protected)]
                        if not self.motion:
                            candidates=[q for q in candidates if all(all(max(abs((q if o is hypothetical else o['point'])[i]-((sum(v['point'][i] for v in members)-hypothetical['point'][i]+q[i])//n)) for i in (0,1))>=5 for o in members) for hypothetical in members)]
                        if candidates:p=candidates[0];reason='probe_group_control'
                    else:
                        current=centers.get(group)
                        path=route(current,g,bad) if current else None
                        choices=[]
                        if path:
                            for distance,q in enumerate(path[1:],1):
                                if set(segment(current,q))&bad:continue
                                for member in members:
                                    others=[o for o in members if o['point']!=member['point']]
                                    for ry,rx in itertools.product(range(n),repeat=2):
                                        dest=tuple(n*q[i]-sum(o['point'][i] for o in others)+(ry,rx)[i] for i in (0,1))
                                        if dest in bad or not(3<=dest[0]<61 and 3<=dest[1]<61):continue
                                        if any(max(abs(dest[i]-z[i]) for i in (0,1))<5 for z in protected):continue
                                        if any(max(abs((dest if o is member else o['point'])[i]-q[i]) for i in (0,1))<5 for o in members):continue
                                        if max(abs(dest[i]-member['point'][i]) for i in (0,1))<3:continue
                                        if any(max(abs(dest[i]-o['point'][i]) for i in (0,1))<5 for o in ends if o['point']!=member['point']):continue
                                        # Click movement may be discontinuous; destination and group-center constraints remain explicit.
                                        if (member['point'],dest) in tried:continue
                                        choices.append((distance,member['point']==at,-sum(abs(dest[i]-member['point'][i]) for i in (0,1)),member['point'],dest,q))
                        if not choices and len(members)>=2:
                            joint=[]
                            for first in members:
                                for second in members:
                                    if first is second:continue
                                    fixed=[o for o in members if o is not first and o is not second]
                                    for ay in range(3,61):
                                        for ax in range(3,61):
                                            a=(ay,ax)
                                            if any(max(abs(a[i]-z[i]) for i in (0,1))<5 for z in protected):continue
                                            if a in bad or a==first['point'] or max(abs(a[i]-first['point'][i]) for i in (0,1))<3:continue
                                            if any(max(abs(a[i]-o['point'][i]) for i in (0,1))<5 for o in ends if o is not first):continue
                                            interim=tuple((sum(o['point'][i] for o in members)-first['point'][i]+a[i])//n for i in (0,1))
                                            if interim in bad:continue
                                            if any(max(abs((a if o is first else o['point'])[i]-interim[i]) for i in (0,1))<5 for o in members):continue
                                            for ry,rx in itertools.product(range(n),repeat=2):
                                                b=tuple(n*g[i]-sum(o['point'][i] for o in fixed)-a[i]+(ry,rx)[i] for i in (0,1))
                                                if b in bad or not(3<=b[0]<61 and 3<=b[1]<61):continue
                                                if any(max(abs(b[i]-z[i]) for i in (0,1))<5 for z in protected):continue
                                                if any(max(abs(pos[i]-g[i]) for i in (0,1))<5 for pos in [a,b]+[o['point'] for o in fixed]):continue
                                                if max(abs(a[i]-b[i]) for i in (0,1))<5:continue
                                                if any(max(abs(b[i]-o['point'][i]) for i in (0,1))<5 for o in ends if o is not first and o is not second):continue
                                                if (first['point'],a) in tried:continue
                                                score=sum(abs(a[i]-first['point'][i])+abs(b[i]-second['point'][i]) for i in (0,1))
                                                joint.append((score,first['point']!=at,first['point'],a,b,interim,second['point']))
                            if joint:
                                _,_,origin,dest,other,interim,second=min(joint)
                                c['pair_relocation_hypothesis']=dict(first_origin=origin,first_destination=dest,second_origin=second,second_destination=other)
                                if origin!=at:p=origin;reason='select_member_for_pair_relocation'
                                else:p=dest;reason='test_pair_relocation';c.update(centroid_target=interim,current_centroid=current,assigned_destination=dest)
                        if choices:
                            _,_,_,origin,dest,q=max(choices)
                            if origin!=at:p=origin;reason='select_member_for_joint_center_route'
                            else:p=dest;reason='route_group_center';c.update(centroid_target=q,current_centroid=current,assigned_destination=dest,centroid_path=path)
                    if p is not None and tuple(p) not in {o['point'] for o in ends}:tried.add((at,tuple(p)))
        if action==6 and p is None:action=None
        c.update(action=action,click=p,reason=reason)
        response=dict(action=action,data={} if p is None else dict(x=p[1],y=p[0]),done=action is None,certificate=c if action==6 else None,advisor='group_centroid_learner',diagnostics=dict(reason=reason,retained_transitions=len(self.history),motion_evidence=len(self.motion),selection_evidence=len(self.swaps),goal_outcomes=copy.deepcopy(self.goal_outcomes)))
        self.previous=copy.deepcopy(obs);self.last=copy.deepcopy(response);return response
