"""Transfer contact-retreat evidence into tentative symbol and centroid plans."""
import copy,itertools
from collections import Counter,deque
from anonymous_link_inquiry_v2 import Agent as Inquiry,BODY
from anonymous_link_scene_v2 import parse
from group_symbolic_scene_v1 import RING
from group_centroid_learner_v14 import blocked,route,segment
from visual_transform_learner import digest

def pattern(obs,center):
    y,x=center
    return tuple(obs['frame'][y+a][x+b] for a,b in BODY)

def inventory(obs):
    ends,pads,groups=parse(obs);f=obs['frame'];bg=Counter(v for row in f for v in row).most_common(1)[0][0]
    rings=[]
    for y in range(3,61):
        for x in range(3,61):
            vals=[f[y+a][x+b] for a,b in RING]
            if bg in vals:continue
            if any(f[y+a][x+b]!=bg for a in range(-3,4) for b in range(-3,4) if (a,b) not in RING):continue
            rings.append(dict(center=(y,x),signature=sorted(set(vals)),points=[(y+a,x+b) for a,b in RING],point_colors=vals,source=digest(obs)))
    for p in pads:p.update(pattern=pattern(obs,p['center']),source=digest(obs))
    return ends,pads,groups,rings

def compatible(state,goal):
    if set(state)!=set(goal['signature']):return False
    for (dy,dx),color in zip(RING,goal['point_colors']):
        norm=(dy*dy+dx*dx)**0.5
        choices=[i for i,(a,b) in enumerate(BODY) if a or b]
        j=min(choices,key=lambda i:sum((BODY[i][k]/(sum(v*v for v in BODY[i])**0.5)-(dy,dx)[k]/norm)**2 for k in (0,1)))
        if state[j]!=color:return False
    return True

class Agent:
    def __init__(self):
        self.prior=Inquiry();self.previous=None;self.last=None;self.history={};self.observations={};self.scene=None;self.symbol_evidence=[];self.contact=None;self.planning=False;self.steps=0;self.assignments={};self.finished={};self.intent=None;self.failures=[];self.attempted={};self.old_groups=[];self.level=None;self.restarted=False;self.awaiting_reset=False;self.consumed=set();self.resource_evidence=[];self.marker_states={};self.marker_interpretations={}
    def marker_pattern(self,obs,g):
        actual=pattern(obs,g['center']);allowed=set().union(*(set(p['signature']) for p in self.scene[1]));c=(self.last or {}).get('certificate') or {};candidates=[]
        if c.get('kind')=='anonymous_link_symbol_plan' and c['group']['key']==g['key'] and self.previous['levels_completed']==obs['levels_completed']:candidates.append(tuple(c['plan']['predicted_pattern']))
        if g['key'] in self.marker_states:candidates.append(self.marker_states[g['key']])
        for expected in candidates:
            differing=[i for i,(a,b) in enumerate(zip(actual,expected)) if a!=b]
            if differing and len(differing)<=3 and all(actual[i] not in allowed and expected[i] in allowed for i in differing):
                self.marker_states[g['key']]=expected;self.marker_interpretations[g['key']]=dict(source=digest(obs),center=g['center'],observed_pattern=actual,interpreted_pattern=expected,occluded_offsets=[BODY[i] for i in differing],known_symbols=sorted(allowed),interpretation='sparse_foreground_occlusion_hypothesis');return expected
        self.marker_states[g['key']]=actual;self.marker_interpretations.pop(g['key'],None);return actual
    def extract(self,obs):
        expected=[copy.deepcopy(o) for g in self.old_groups for o in g['members']]
        c=(self.last or {}).get('certificate') or {}
        if c.get('kind')=='anonymous_link_symbol_plan' and not c['selection_probe']:
            for o in expected:
                if tuple(o['point'])==tuple(c['origin']):o['point']=tuple(c['destination'])
        return parse(obs,expected)
    def observe(self,obs):
        self.observations[digest(obs)]=copy.deepcopy(obs)
        if self.previous is None:return
        event=dict(before=self.previous,action=self.last['action'],data=self.last['data'],after=copy.deepcopy(obs));source=digest(event);self.history[source]=event
        c=self.last.get('certificate') or {}
        if c.get('kind') in ('anonymous_link_interaction_probe','anonymous_link_symbol_plan') and not c.get('selection_probe'):
            center=tuple(c['predicted_center']);before=pattern(self.previous,c['group']['center']);after=pattern(obs,center)
            if obs['levels_completed']==self.previous['levels_completed']:
                target=c['target']
                if target.get('signature') and max(abs(center[i]-target['center'][i]) for i in (0,1))<=1:
                    self.consumed.add(tuple(target['center']));self.contact=dict(contact_source=source,before_center=c["group"]["center"],contact_center=center,before_pattern=before,after_pattern=after,site=copy.deepcopy(target),member_count=len(c['group']['members']))
                elif self.contact and after==tuple(self.contact['after_pattern']) and max(abs(center[i]-self.contact['site']['center'][i]) for i in (0,1))>=6:
                    q=dict(self.contact,retreat_source=source,retreat_center=center)
                    if q['before_pattern']!=q['after_pattern']:
                        self.symbol_evidence.append(q)
                        if pattern(obs,q['site']['center'])!=tuple(q['site'].get('pattern',pattern(self.observations[self.scene[1][0]['source']],q['site']['center']))):self.resource_evidence.append(dict(site=q['site']['center'],source=source,initial_source=self.scene[1][0]['source'],reason='site_pattern_absent_after_retreat'))
                    self.contact=None
            if self.planning and not c.get('selection_probe'):
                _,_,groups=self.extract(obs)
                if not any(tuple(g['center'])==center for g in groups):self.failures.append(dict(source=source,reason='predicted_center_not_observed',predicted=center))
        self.contact=self.contact if obs['levels_completed']==self.previous['levels_completed'] else None
    def remember(self,obs,response):
        self.previous=copy.deepcopy(obs);self.last=copy.deepcopy(response);return response
    def respond(self,obs):
        self.observe(obs)
        if self.awaiting_reset:
            self.scene=inventory(obs);self.old_groups=[];self.assignments={};self.finished={};self.intent=None;self.consumed=set();self.marker_states={};self.marker_interpretations={};self.awaiting_reset=False
        if not self.planning:
            if self.prior.prior.active_color is None:
                observed_ends,_,_=parse(obs);counts=Counter(o['color'] for o in observed_ends)
                if counts:self.prior.prior.active_color=min(counts,key=lambda k:(counts[k],k))
            candidate=self.prior.respond(obs)
            if self.prior.exploring and self.scene is None:
                initial=self.prior.previous if self.prior.previous else obs
                self.scene=inventory(initial);self.level=obs['levels_completed']
            if not candidate['done'] or obs['state']!='NOT_FINISHED':return self.remember(obs,candidate)
            if self.scene is None:return self.remember(obs,candidate)
            self.planning=True
        if not self.restarted and len(self.resource_evidence)>=2:
            self.restarted=True;self.awaiting_reset=True;self.contact=None
            response=dict(action=0,data={},done=False,certificate=dict(kind='anonymous_resource_restart',context=digest(obs),resource_evidence=copy.deepcopy(self.resource_evidence),retained_symbol_evidence=copy.deepcopy(self.symbol_evidence),reason='consumed_sites_make_current_allocation_infeasible'),advisor='anonymous_symbol_learner',diagnostics=dict(reason='retain_discovery_and_restart_allocation'))
            return self.remember(obs,response)
        if obs['levels_completed']!=self.level and obs['state']=='NOT_FINISHED':
            candidate=inventory(obs)
            if candidate[1] and candidate[2] and candidate[3]:
                self.scene=candidate;self.level=obs['levels_completed'];self.old_groups=[];self.assignments={};self.finished={};self.intent=None;self.consumed=set();self.marker_states={};self.marker_interpretations={};self.steps=0;self.contact=None;self.restarted=True
        if obs['levels_completed']!=self.level or obs['state']!='NOT_FINISHED':
            return self.remember(obs,dict(action=None,data={},done=True,certificate=None,advisor='anonymous_symbol_learner',diagnostics=dict(reason='new_scene_requires_interpretation',symbol_evidence=len(self.symbol_evidence))))
        ends,pads_now,groups=self.extract(obs);pads=self.scene[1];goals=self.scene[3];active_color=self.prior.prior.active_color;active=next((o for o in ends if o['color']==active_color),None)
        groups=sorted(groups,key=lambda g:(len(g['members']),g['center']));bad=blocked(obs,ends)
        # Initial identity is maintained by shared stationary endpoints; moves are explicit.
        if not self.old_groups:
            self.old_groups=[dict(g,key=str(i)) for i,g in enumerate(groups)]
        current=[];used=set()
        for old in self.old_groups:
            opts=[g for g in groups if id(g) not in used]
            if not opts:continue
            g=max(opts,key=lambda g:(len({tuple(o['point']) for o in old['members']} & {tuple(o['point']) for o in g['members']}),len(g['members'])==len(old['members'])))
            if len(g['members'])!=len(old['members']):continue
            used.add(id(g));current.append(dict(g,key=old['key']))
        self.old_groups=copy.deepcopy(current)
        empty=set.intersection(*(set(p['signature']) for p in pads)) if pads else set()
        blank=next(iter(empty)) if len(empty)==1 else None
        supported={tuple(q['site']['center']):q for q in self.symbol_evidence}
        operations=[]
        for p in pads:
            if len(self.symbol_evidence)>=2 and tuple(p['center']) not in self.consumed:
                operations.append(p)
        for g in current:
            goal=self.assignments.get(g['key'])
            if goal and tuple(g['center'])==tuple(goal['center']) and compatible(self.marker_pattern(obs,g),goal):self.finished[g['key']]=goal
        unresolved=[g for g in current if g['key'] not in self.finished]
        g=next((g for g in unresolved if active in g['members']),unresolved[0] if unresolved else None)
        target=None;plan=None;reason='unresolved_symbol_goal'
        if g and active and self.steps<160 and blank is not None:
            if self.intent and self.intent['group_key']==g['key']:
                target=self.intent['target']
                if tuple(g['center'])==tuple(target['center']):self.intent=None;target=None
            if target is None:
                occupied={tuple(v['center']) for k,v in self.finished.items() if k!=g['key']}
                start=self.marker_pattern(obs,g);queue=deque([(start,[])]);seen={start};solutions=[]
                while queue:
                    state,path=queue.popleft()
                    for goal in goals:
                        if tuple(goal['center']) in occupied:continue
                        if compatible(state,goal) and blank not in state:
                            solutions.append((len(path),sum(abs(g['center'][i]-(path[0]['center'] if path else goal['center'])[i]) for i in (0,1)),goal,path,state))
                    if len(path)>=3:continue
                    for site in operations:
                        state2=tuple(site['pattern'][i] if site['pattern'][i]!=blank else state[i] for i in range(len(BODY)))
                        if state2 not in seen:seen.add(state2);queue.append((state2,path+[site]))
                if solutions:
                    _,_,goal,path,state=min(solutions,key=lambda q:(q[0],q[1],q[2]['center']))
                    self.assignments[g['key']]=goal;target=path[0] if path else dict(goal,signature=[])
                    plan=dict(goal=goal,sites=path,predicted_pattern=state,blank=blank,interpretation='observed_spatial_overwrite_transfer_hypothesis',supported_sites=copy.deepcopy(self.symbol_evidence),novel_masks_are_transfer_hypotheses=True)
                    self.intent=dict(group_key=g['key'],target=copy.deepcopy(target),plan=copy.deepcopy(plan))
            else:plan=self.intent['plan']
        action=None;data={};cert=None
        if target and g and active:
            path=route(g['center'],target['center'],bad);choices=[];n=len(g['members']);protected=[v['center'] for v in current if v['key']!=g['key']]
            for distance,q in enumerate(path or []):
                if not distance:continue
                for member in g['members']:
                    for rem in itertools.product(range(n),repeat=2):
                        dest=tuple(n*q[i]-sum(o['point'][i] for o in g['members'] if o is not member)+rem[i] for i in (0,1))
                        if not(3<=dest[0]<61 and 3<=dest[1]<61) or dest in bad:continue
                        if max(abs(dest[i]-member['point'][i]) for i in (0,1))<3:continue
                        if any(max(abs(dest[i]-o['point'][i]) for i in (0,1))<5 for o in ends if o is not member):continue
                        if any(max(abs(dest[i]-c[i]) for i in (0,1))<5 for c in protected+[q]):continue
                        if any(max(abs((dest if o is member else o['point'])[i]-q[i]) for i in (0,1))<5 for o in g['members']):continue
                        # Preserve learned colors while routing to a goal; crossing is a hypothesis, destination contact is checked.
                        if not target.get('signature') and any(max(abs(q[i]-p['center'][i]) for i in (0,1))<=2 for p in pads):continue
                        choices.append((distance,member is active,-sum(abs(dest[i]-member['point'][i]) for i in (0,1)),member['point'],dest,q))
            pair=None
            if not choices:
                pairs=[];goal=tuple(target['center'])
                for first in g['members']:
                    for second in g['members']:
                        if first is second:continue
                        fixed=[o for o in g['members'] if o is not first and o is not second]
                        for ay in range(3,61):
                            for ax in range(3,61):
                                a=(ay,ax)
                                if a in bad or max(abs(a[i]-first['point'][i]) for i in (0,1))<3:continue
                                if any(max(abs(a[i]-o['point'][i]) for i in (0,1))<5 for o in ends if o is not first):continue
                                if any(max(abs(a[i]-p[i]) for i in (0,1))<5 for p in protected):continue
                                interim=tuple((sum(o['point'][i] for o in g['members'])-first['point'][i]+a[i])//n for i in (0,1))
                                if interim in bad or set(segment(g['center'],interim))&bad:continue
                                if any(max(abs((a if o is first else o['point'])[i]-interim[i]) for i in (0,1))<5 for o in g['members']):continue
                                if any(max(abs(interim[i]-p['center'][i]) for i in (0,1))<=3 for p in pads if tuple(p['center']) not in self.consumed):continue
                                for rem in itertools.product(range(n),repeat=2):
                                    b=tuple(n*goal[i]-sum(o['point'][i] for o in fixed)-a[i]+rem[i] for i in (0,1))
                                    if b in bad or not(3<=b[0]<61 and 3<=b[1]<61):continue
                                    if max(abs(a[i]-b[i]) for i in (0,1))<5:continue
                                    if any(max(abs(b[i]-o['point'][i]) for i in (0,1))<5 for o in ends if o is not first and o is not second):continue
                                    if any(max(abs(p[i]-goal[i]) for i in (0,1))<5 for p in [a,b]+[o['point'] for o in fixed]):continue
                                    if any(max(abs(b[i]-p[i]) for i in (0,1))<5 for p in protected):continue
                                    score=sum(abs(a[i]-first['point'][i])+abs(b[i]-second['point'][i]) for i in (0,1))
                                    pairs.append((score,first is not active,first['point'],a,b,interim,second['point']))
                if pairs:
                    _,_,origin,dest,other,interim,second=min(pairs);choices.append((0,origin==active['point'],0,origin,dest,interim));pair=dict(first_origin=origin,first_destination=dest,second_origin=second,second_destination=other,goal=goal)
            if choices:
                _,_,_,origin,dest,center=max(choices);select=origin!=active['point'];click=origin if select else dest
                action=6;data=dict(y=click[0],x=click[1]);reason='select_group_member' if select else 'test_symbol_goal_plan';self.steps+=1
                cert=dict(kind='anonymous_link_symbol_plan',context=digest(obs),action=6,click=click,group=g,target=copy.deepcopy(target),origin=origin,destination=dest,predicted_center=center,selection_probe=select,goal_is_hypothesis=True,plan=plan,inventory_source=pads[0]['source'],retained_outcomes=copy.deepcopy(self.prior.outcomes),resource_evidence=copy.deepcopy(self.resource_evidence),consumed_sites=sorted(self.consumed),partial_visibility_hypothesis=True,marker_interpretations=copy.deepcopy(self.marker_interpretations),paired_relocation=pair,failures=copy.deepcopy(self.failures))
        response=dict(action=action,data=data,done=action is None,certificate=cert,advisor='anonymous_symbol_learner',diagnostics=dict(reason=reason,symbol_evidence=len(self.symbol_evidence),finished=copy.deepcopy(self.finished),steps=self.steps,failures=copy.deepcopy(self.failures)))
        return self.remember(obs,response)
