"""Learn visible symbol transformations through movement and compare goal glyphs."""
import copy
from conditional_goal_motion_v1 import regions as conditional_regions,relaxed as relaxed_goal_motion
from key_motion_frontier_v1 import marks as edge_marks,frontier as motion_frontier
from key_control_clock_v3 import observed_at,learn as learn_clock,at as control_at,refresh as refresh_controls,intercept
from collections import Counter,deque
from binary_demonstration_bootstrap_v1 import components
from key_resource_planning_v18 import discover as discover_meter,value as meter_value,search as resource_plan
DIRS={1:(-1,0),2:(1,0),3:(0,-1),4:(0,1)}
def inside(p,b):return b[0]<=p[0]<b[0]+b[2]and b[1]<=p[1]<b[1]+b[3]
def glyph(frame,box,ink):
    pts=[(y,x)for y in range(box[0],box[0]+box[2])for x in range(box[1],box[1]+box[3])if frame[y][x]==ink]
    if not pts:return None
    y0,x0=min(p[0]for p in pts),min(p[1]for p in pts);h=max(p[0]for p in pts)-y0+1;w=max(p[1]for p in pts)-x0+1
    for k in range(min(h,w),0,-1):
        if h%k or w%k:continue
        if all(len({frame[y][x]==ink for y in range(y0+r,y0+r+k)for x in range(x0+c,x0+c+k)})==1 for r in range(0,h,k)for c in range(0,w,k)):
            return tuple(tuple(int(frame[y0+r][x0+c]==ink)for c in range(0,w,k))for r in range(0,h,k))
def transform(g,op):
    if op>=4:g=tuple(tuple(reversed(r))for r in g);op-=4
    for _ in range(op):g=tuple(tuple(r)for r in zip(*g[::-1]))
    return g
def perceive(frame,identity=None,retained=None,goal_contacts=(),goal_barriers=()):
    obs=components(frame);pairs=[]
    for i,a in enumerate(obs):
        y,x,h,w=a['box']
        if len(a['shape'])!=h*w or not 1<=min(h,w)<=4 or max(h,w)>9:continue
        for b in obs[i+1:]:
            yy,xx,hh,ww=b['box']
            if len(b['shape'])!=hh*ww or a['ink']==b['ink']:continue
            if identity is not None and {a['ink'],b['ink']}!=set(identity):continue
            if x==xx and w==ww and(y+h==yy or yy+hh==y)and h+hh==w:box=(min(y,yy),x,w,w)
            elif y==yy and h==hh and(x+w==xx or xx+ww==x)and w+ww==h:box=(y,min(x,xx),h,h)
            else:continue
            if 3<=box[2]<=9:pairs.append((box,(a['ink'],b['ink'])))
    candidates=[]
    for box,inks in pairs:
        frames=[o for o in obs if 5<=o['box'][2]==o['box'][3]<=15 and len(o['shape'])<o['box'][2]**2 and all((r,c)in o['shape']for r,c in[(0,0),(0,o['box'][2]-1),(o['box'][2]-1,0),(o['box'][2]-1,o['box'][2]-1)])]
        framed=[]
        if retained:
            for field,border in [('hud',retained['hud_border']),('goal',retained['goal_border'])]:
                bounds=retained[field]
                if field=='goal':
                    for g in retained.get('goal_options',[dict(box=bounds,border=border,color=retained['target_color'],glyph=retained['target'])]):
                        framed.append((dict(box=g['box'],ink=g['border']),g['color'],g['glyph']))
                    continue
                colors=Counter(frame[y][x]for y in range(bounds[0],bounds[0]+bounds[2])for x in range(bounds[1],bounds[1]+bounds[3])if frame[y][x]!=border)
                if colors:
                    ink=colors.most_common(1)[0][0];framed.append((dict(box=bounds,ink=border),ink,glyph(frame,bounds,ink)))
        else:
            for o in frames:
                y,x,h,w=o['box'];colors=Counter(frame[yy][xx]for yy in range(y,y+h)for xx in range(x,x+w)if frame[yy][xx]!=o['ink'])
                if colors:
                    ink=colors.most_common(1)[0][0];framed.append((o,ink,glyph(frame,o['box'],ink)))
        framed=[v for v in framed if v[2]and 2<=len(v[2])<=5 and 2<=len(v[2][0])<=5]
        if len(framed)<2:continue
        framed.sort(key=lambda v:(min(v[0]['box'][0],v[0]['box'][1],64-v[0]['box'][0]-v[0]['box'][2],64-v[0]['box'][1]-v[0]['box'][3]),-v[0]['box'][2]))
        hud=framed[0];options=framed[1:];counts=Counter(tuple(r['goal'])for r in goal_contacts);goal=min(options,key=lambda v:(counts[tuple(v[0]['box'])],0 if any(tuple(r['goal'])==tuple(v[0]['box'])for r in goal_barriers)else 1,0 if retained and tuple(v[0]['box'])==tuple(retained['goal'])else 1,0 if v[1]==hud[1]else 1,sum(abs(v[0]['box'][k]-box[k])for k in(0,1)),v[0]['box']));candidates.append(dict(goal_options=[dict(box=g[0]['box'],border=g[0]['ink'],color=g[1],glyph=g[2])for g in options],actor=box,identity=inks,ink=hud[1],key_color=hud[1],target_color=goal[1],key=hud[2],target=goal[2],hud=hud[0]['box'],goal=goal[0]['box'],hud_border=hud[0]['ink'],goal_border=goal[0]['ink']))
    if len(candidates)!=1:return None
    s=candidates[0];floor_candidates=[o for o in obs if len(o['shape'])>=50 and o['box'][0]>0 and o['box'][1]>0 and o['box'][0]+o['box'][2]<64 and o['box'][1]+o['box'][3]<64 and o['ink']not in s['identity']]
    if not floor_candidates:return None
    floor=dict(max(floor_candidates,key=lambda o:len(o['shape'])));parts=[o['box']for o in floor_candidates if o['ink']==floor['ink']and min(o['box'][2:])>=s['actor'][2]];y=min(b[0]for b in parts);x=min(b[1]for b in parts);floor['box']=(y,x,max(b[0]+b[2]for b in parts)-y,max(b[1]+b[3]for b in parts)-x);s['floor']=floor['ink'];s['floor_box']=floor['box'];pixels={};boundary=Counter(frame[0]+frame[-1]+[row[0]for row in frame]+[row[-1]for row in frame]).most_common(1)[0][0]
    for o in obs:
        if len(o['shape'])>30 or o['ink']in(s['floor'],boundary)or any(inside(o['box'][:2],s[k])for k in('actor','hud'))or any(inside(o['box'][:2],g['box'])for g in s['goal_options']):continue
        for dy,dx in o['shape']:
            p=o['box'][0]+dy,o['box'][1]+dx
            if inside(p,floor['box']):pixels[p]=o['ink']
    controls=[]
    while pixels:
        seed=min(pixels);queue=[seed];found=[]
        while queue:
            p=queue.pop()
            if p not in pixels:continue
            ink=pixels.pop(p);found.append((*p,ink));queue.extend((p[0]+dy,p[1]+dx)for dy in(-1,0,1)for dx in(-1,0,1)if dy or dx)
        ys=[v[0]for v in found];xs=[v[1]for v in found];by,bx=min(ys),min(xs);bh,bw=max(ys)-by+1,max(xs)-bx+1
        if 2<=bh<=7 and 2<=bw<=7:
            signature=tuple(sorted((y-by,x-bx,ink)for y,x,ink in found));controls.append(dict(box=(by,bx,bh,bw),signature=signature))
    s['controls']=controls;return s
def covers(position,n,control):
    y,x,h,w=control['box'];return position[0]<=y+h//2<position[0]+n and position[1]<=x+w//2<position[1]+n
def route(start,goal,mask,n,controls,avoid=True,motion=None):
    motion=motion or {}
    queue=deque([(start,[])]);seen={start}
    while queue:
        p,path=queue.popleft()
        if goal(p):return path
        for action,(dy,dx)in DIRS.items():
            q=motion.get((p,action,n),(p[0]+dy*n,p[1]+dx*n))
            if q in seen or not all((y,x)in mask for y in range(q[0],q[0]+n)for x in range(q[1],q[1]+n)):continue
            if avoid and any(covers(q,n,c)and not covers(p,n,c)for c in controls):continue
            seen.add(q);queue.append((q,path+[action]))
    return None
class Agent:
    def __init__(self,prior=None):
        self.prior=prior;self.active=True;self.identity=None;self.level=None;self.previous=None;self.t=0;self.mask=set();self.controls=[];self.rules={};self.evidence=[];self.failures=[];self.archive=[];self.visits=Counter();self.restarts=0;self.plan=[];self.scene_prior=None;self.meter=None;self.resource_evidence=[];self.resource_rules=set();self.consumed=set();self.resource_costs=[];self.color_rules={};self.shape_rules={};self.motion={};self.control_history={};self.control_clocks={};self.clock_ticks={};self.movement_tick=0;self.portal_marks=set();self.portal_evidence=[];self.stationary_failures=[];self.goal_frontier_level=None;self.goal_contacts=[];self.goal_barriers=[]
    def respond(self,raw):
        s=perceive(raw['frame'],self.identity,self.scene_prior if raw['levels_completed']==self.level else None,[r for r in self.goal_contacts if r['level']==raw['levels_completed']],[r for r in self.goal_barriers if r['level']==raw['levels_completed']])
        if s and self.previous and raw['state']=='NOT_FINISHED' and raw['levels_completed']==self.level:
            b=self.previous['scene'];g=b['goal'];n=s['actor'][2];target=(g[0]+(g[2]-n)//2,g[1]+(g[3]-n)//2)
            if len(b.get('goal_options',[]))>1 and b['actor']==s['actor']:
                dy,dx=DIRS[self.previous['action']];q=(b['actor'][0]+dy*n,b['actor'][1]+dx*n)
                for option in b['goal_options']:
                    if covers(q,n,dict(box=option['box']))and (s['key']!=option['glyph']or s['key_color']!=option['color']):
                        witness=dict(level=self.level,source=self.previous['source'],goal=option['box'],hypothesis='blocked_entry_into_unmatched_goal_region_may_require_this_goal_first')
                        if witness not in self.goal_barriers:self.goal_barriers.append(witness)
                s=perceive(raw['frame'],self.identity,self.scene_prior,[r for r in self.goal_contacts if r['level']==self.level],[r for r in self.goal_barriers if r['level']==self.level])

            if len(b.get('goal_options',[]))>1 and s['actor'][:2]==target and b['actor'][:2]!=target and s['key']==b['target'] and s['key_color']==b['target_color']:
                self.goal_contacts.append(dict(level=self.level,source=self.previous['source'],goal=g,hypothesis='matched_goal_contact_without_level_completion'))
                s=perceive(raw['frame'],self.identity,self.scene_prior,[r for r in self.goal_contacts if r['level']==self.level],[r for r in self.goal_barriers if r['level']==self.level])
        if s and raw['state']=='NOT_FINISHED':
            if raw['levels_completed']!=self.level:self.control_history={};self.control_clocks={};self.clock_ticks={};self.movement_tick=0
            if self.previous and raw['levels_completed']==self.level and s['actor'][:2]!=self.previous['scene']['actor'][:2]:self.movement_tick+=1
            self.clock_ticks[self.t]=self.movement_tick
            learn_clock(self.control_history,self.control_clocks,s['controls'],self.t,self.clock_ticks,s['actor'])
        if self.previous and s and raw['levels_completed']==self.level:
            p=self.previous;b=p['scene'];entered=[control_at(c,self.control_clocks,self.t)for c in self.controls if covers(s['actor'][:2],s['actor'][2],control_at(c,self.control_clocks,self.t))and not covers(b['actor'][:2],b['actor'][2],observed_at(c,self.control_clocks,p['source'],self.clock_ticks))]
            self.motion[(b['actor'][:2],p['action'],b['actor'][2])]=s['actor'][:2]
            for c in entered:self.visits[c['box']]+=1
            if self.meter:
                previous_value=p['meter_value'];current_value=meter_value(raw['frame'],self.meter);self.meter['capacity']=max(self.meter['capacity'],current_value)
                resource=dict(source=p['source'],box=self.meter['box'],ink=self.meter['ink'],before=previous_value,after=current_value,entered=copy.deepcopy(entered));self.resource_evidence.append(resource)
                if 0<previous_value-current_value<=self.meter['capacity']//4:self.resource_costs.append(previous_value-current_value)
                if current_value>previous_value:
                    for control in entered:self.resource_rules.add(control['signature']);self.consumed.add(control['box'])
                if current_value>previous_value and not entered and sum(abs(a-b)for a,b in zip(s['actor'][:2],b['actor'][:2]))>b['actor'][2]:
                    self.motion.pop((b['actor'][:2],p['action'],b['actor'][2]),None)
                    self.failures.append(dict(source=p['source'],kind='unrequested_position_reset',before=b['actor'],after=s['actor']));self.consumed=set();self.visits=Counter();self.control_history={};self.control_clocks={};self.clock_ticks={};self.movement_tick=0;self.controls=[]
            dy,dx=DIRS[p['action']];ordinary=(b['actor'][0]+dy*b['actor'][2],b['actor'][1]+dx*b['actor'][2])
            if s['actor'][:2]!=b['actor'][:2] and s['actor'][:2]!=ordinary and not any(f['source']==p['source'] and f['kind']=='unrequested_position_reset'for f in self.failures):
                found=edge_marks(p['frame'],ordinary,b['actor'][2],b['floor'],b['identity'])
                if found:
                    self.portal_marks.update(ink for _,ink in found);self.portal_evidence.append(dict(source=p['source'],expected_tile=ordinary,marks=found))
            r=dict(source=p['source'],action=p['action'],before=b['actor'],after=s['actor'],key_before=b['key'],key_after=s['key'],color_before=b['key_color'],color_after=s['key_color'],entered=copy.deepcopy(entered),state=raw['state']);self.evidence.append(r)
            if b['actor']==s['actor'] and b['key']==s['key'] and b['key_color']==s['key_color']:
                for control in entered:
                    if control['signature'] in self.control_clocks and self.rules.get(control['signature'],{0})!={0}:
                        self.stationary_failures.append(dict(source=p['source'],signature=control['signature'],level=self.level,hypothesis='stationary_contact_did_not_apply_predicted_symbol_change'))
            if b['key_color']!=s['key_color']:
                for control in entered:self.color_rules.setdefault(control['signature'],{})[b['key_color']]=s['key_color']
            if b['key']!=s['key']:
                for control in entered:self.shape_rules.setdefault(control['signature'],{})[b['key']]=s['key']
                self.plan=[]
                for c in entered:
                    matched={op for op in range(8)if transform(b['key'],op)==s['key']};previous=self.rules.get(c['signature'],set(range(8)));self.rules[c['signature']]=(previous&matched)or matched
            if b['actor']==s['actor']:self.failures.append(dict(source=p['source'],kind='blocked_movement',position=b['actor'][:2],action=p['action']));self.plan=[]
            if b['key']==s['key']and entered:
                for c in entered:
                    if c['signature']not in self.rules:self.rules[c['signature']]={0}
        self.previous=None
        if raw['state']=='GAME_OVER':
            if self.restarts>=3:return dict(done=True,action=None,data={})
            self.restarts+=1;self.plan=[];self.t+=1;self.control_history={};self.control_clocks={};self.clock_ticks={};self.movement_tick=0;self.controls=[];self.consumed=set();self.visits=Counter()
            return dict(done=False,action=0,data={},certificate=dict(kind='key_glyph',source=self.t-1,tag='retry_retaining_symbol_models',scene=None,evidence=copy.deepcopy(self.evidence),failures=copy.deepcopy(self.failures),archive=copy.deepcopy(self.archive)))
        if raw['state']!='NOT_FINISHED'or s is None:return dict(done=True,action=None,data={})
        if self.identity is None:self.identity=s['identity']
        self.scene_prior=s
        if self.level!=raw['levels_completed']:
            if self.level is not None:self.archive.append(dict(level=self.level,evidence_count=len(self.evidence),failures_count=len(self.failures)))
            self.level=raw['levels_completed'];self.controls=[];self.mask=set();self.visits=Counter();self.plan=[];self.restarts=0;self.consumed=set();self.meter=None;self.motion={};self.resource_costs=[]
        if self.meter is None:self.meter=discover_meter(raw['frame'],s)
        f=raw['frame'];self.mask.update((y,x)for y in range(64)for x in range(64)if f[y][x]==s['floor']or inside((y,x),s['actor'])or any(inside((y,x),g['box'])for g in s['goal_options']))
        self.controls=refresh_controls(self.controls,s['controls'],self.control_clocks,self.t,s['actor'])
        for c in self.controls:self.mask.update((y,x)for y in range(c['box'][0],c['box'][0]+c['box'][2])for x in range(c['box'][1],c['box'][1]+c['box'][3]))
        pos=s['actor'][:2];n=s['actor'][2];tag='test_symbol_goal';path=None
        goal_models=conditional_regions(s,self.goal_barriers,self.goal_contacts,self.level);planning_scene=dict(s,conditional_goal_regions=goal_models)
        motion=relaxed_goal_motion(self.motion,[g for g in goal_models if g['glyph']==s['key']and g['color']==s['key_color']])
        if self.meter and self.resource_costs:
            cost=sorted(self.resource_costs)[len(self.resource_costs)//2];path=resource_plan(planning_scene,self.mask,self.controls,self.rules,self.shape_rules,self.color_rules,self.resource_rules,self.consumed,self.meter,meter_value(raw['frame'],self.meter),cost,motion,self.control_clocks,self.t,stationary_rejected=(any(v['level']==self.level for v in self.stationary_failures)or any(v.get('basis')=='movement'for v in self.control_clocks.values())));tag='compose_symbol_and_resource_actions'
        elif self.control_clocks:
            path=resource_plan(planning_scene,self.mask,self.controls,self.rules,self.shape_rules,self.color_rules,self.resource_rules,self.consumed,dict(capacity=128),128,1,motion,self.control_clocks,self.t,stationary_rejected=(any(v['level']==self.level for v in self.stationary_failures)or any(v.get('basis')=='movement'for v in self.control_clocks.values())));tag='compose_symbol_and_resource_actions'
        if not path and s['key']==s['target']and s['key_color']==s['target_color']:
            goal=s['goal'];target=(goal[0]+(goal[2]-n)//2,goal[1]+(goal[3]-n)//2);path=route(pos,lambda p:p==target,self.mask,n,self.controls,motion=motion)
            if path==[]:self.failures.append(dict(source=self.t,kind='goal_symbol_match_without_progress',position=pos));path=None
        frontier_trial=None
        if not path and self.portal_marks:
            inaccessible=[c for c in self.controls if c['signature']not in self.resource_rules and route(pos,lambda p:covers(p,n,c),self.mask,n,[],False,motion)is None]
            g=s['goal'];goal_position=(g[0]+(g[2]-n)//2,g[1]+(g[3]-n)//2)
            if route(pos,lambda p:p==goal_position,self.mask,n,[],False,motion)is None:
                if s['key']==s['target']and s['key_color']==s['target_color']:self.goal_frontier_level=self.level
                if self.goal_frontier_level==self.level:inaccessible.append(dict(box=g,signature=()))
                else:
                    meter=self.meter or dict(capacity=128);cost=sorted(self.resource_costs)[len(self.resource_costs)//2]if self.resource_costs else 1;remaining=meter_value(raw['frame'],meter)if self.meter else 128
                    path=resource_plan(planning_scene,self.mask,self.controls,self.rules,self.shape_rules,self.color_rules,self.resource_rules,self.consumed,meter,remaining,cost,motion,self.control_clocks,self.t,goal_contact=False,stationary_rejected=(any(v['level']==self.level for v in self.stationary_failures)or any(v.get('basis')=='movement'for v in self.control_clocks.values())))
                    if path:tag='compose_symbol_prerequisite_before_goal_exploration'
            if inaccessible and not path:
                frontier_trial=motion_frontier(s,self.mask,motion,self.portal_marks,raw['frame'],inaccessible)
                if frontier_trial:path=frontier_trial['path'];tag='test_surprising_motion_frontier'
        if not path:
            options=[]
            for c in self.controls:
                if c['box']in self.consumed:continue
                sig=c['signature'];known=self.rules.get(sig);wanted=None
                if known or sig in self.shape_rules:
                    g=s['key'];color=s['key_color']
                    for count in range(1,9):
                        g=self.shape_rules.get(sig,{}).get(g,transform(g,min(known)if known else 0));color=self.color_rules.get(sig,{}).get(color,color)
                        if g==s['target']and color==s['target_color']:wanted=count;break
                other=[v for v in self.controls if v!=c]
                if sig in self.control_clocks:
                    candidate=intercept(pos,c,self.mask,n,self.controls,motion,self.control_clocks,self.t,stationary_rejected=(any(v['level']==self.level for v in self.stationary_failures)or any(v.get('basis')=='movement'for v in self.control_clocks.values())))
                elif covers(pos,n,c):
                    candidate=route(pos,lambda p:not covers(p,n,c),self.mask,n,other,motion=motion)
                else:candidate=route(pos,lambda p:covers(p,n,c),self.mask,n,other,motion=motion)
                if candidate:options.append(((0 if known is None or(sig in self.shape_rules and s['key']not in self.shape_rules[sig])or(sig in self.color_rules and s['key_color']not in self.color_rules[sig])else 1 if wanted else 2,self.visits[c['box']],wanted or 9,len(candidate)),c,candidate))
            if options:
                _,control,path=min(options,key=lambda v:v[0]);tag='inquire_symbol_control'
        if not path or self.t>=768:return dict(done=True,action=None,data={})
        action=path[0];c=dict(goal_barriers=copy.deepcopy(self.goal_barriers),clock_ticks=list(self.clock_ticks.items()),goal_contacts=copy.deepcopy(self.goal_contacts),stationary_failures=copy.deepcopy(self.stationary_failures),goal_frontier_level=self.goal_frontier_level,portal_evidence=copy.deepcopy(self.portal_evidence),frontier_trial=frontier_trial,kind='key_glyph',source=self.t,tag=tag,scene=s,evidence=copy.deepcopy(self.evidence),failures=copy.deepcopy(self.failures),archive=copy.deepcopy(self.archive),control_clocks=[dict(signature=k,**v)for k,v in self.control_clocks.items()],control_history=[dict(signature=k,observations=list(v.items()))for k,v in self.control_history.items()],shape_models=[dict(signature=k,edges=list(v.items()))for k,v in self.shape_rules.items()],motion_models=[dict(position=k[0],action=k[1],size=k[2],destination=v)for k,v in self.motion.items()],color_models=[dict(signature=k,mapping=v)for k,v in self.color_rules.items()],resource_evidence=copy.deepcopy(self.resource_evidence),meter=copy.deepcopy(self.meter),resource_rules=list(self.resource_rules),consumed=list(self.consumed),models=[dict(signature=k,operations=sorted(v))for k,v in self.rules.items()],path=path,goal_is_hypothesis=True)
        if goal_models:c['conditional_goal_regions']=copy.deepcopy(goal_models)
        self.previous=dict(source=self.t,frame=copy.deepcopy(raw['frame']),scene=copy.deepcopy(s),action=action,meter_value=meter_value(raw['frame'],self.meter)if self.meter else None);self.t+=1;return dict(done=False,action=action,data={},certificate=c)
