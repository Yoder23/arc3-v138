"""Assign shared-color targets jointly while retaining learned selected-object controls."""
from collections import deque
from itertools import permutations
from structured_interaction_probe_v1 import parts
import copy
from cross_shape_geometry_v2 import scene,shape_points
from visual_transform_learner import digest
from cross_temporal_identity_v4 import Tracker
from cross_color_surface_model_v2 import sites as color_sites,safe as color_safe,infer_margin
class Agent:
    def __init__(self,prior=None):
        self.track=Tracker();self.models=copy.deepcopy(prior.models) if prior else {};self.history=copy.deepcopy(prior.history) if prior else {};self.goal_outcomes=copy.deepcopy(prior.goal_outcomes) if prior else [];self.previous=None;self.last=None;self.level=None;self.targets={};self.source=None;self.calibrated=set();self.calibration=[];self.layout=None;self.layout_key=None;self.radii={};self.color_binding={};self.color_changes=[];self.conversion_targets={};self.object_target_colors={};self.paint_sites=[];self.paint_source=None;self.surface_margin=0;self.surface_evidence=[];self.target_evidence={};self.target_ring_colors=set()
    def observe(self,obs,objs):
        if self.previous is None:return
        e=dict(before=self.previous,action=self.last,data={},after=copy.deepcopy(obs));src=digest(e);self.history[src]=e
        if self.last==0:return
        if obs['levels_completed']>self.previous['levels_completed'] or obs['state']=='WIN':self.goal_outcomes.append(dict(source=src,progress=True,goal='shared_color_shape_coverage'));return
        old,_=self.track.extract(self.previous);changed=[k for k in sorted(old.keys()&objs.keys()) if old[k]['center']!=objs[k]['center']]
        for key in sorted(old.keys()&objs.keys()):
            if old[key]['color']!=objs[key]['color']:
                self.color_changes.append(dict(source=src,before_color=old[key]['color'],after_color=objs[key]['color'],before_center=old[key]['center'],after_center=objs[key]['center'],geometry=old[key]['radius']))
                inferred=infer_margin(objs[key]['center'],old[key]['radius'],objs[key]['color'],self.paint_sites)
                if inferred:
                    pad,margin=inferred;self.surface_margin=max(self.surface_margin,margin);self.surface_evidence.append(dict(source=src,site_source=self.paint_source,site=copy.deepcopy(pad),margin=margin,center=objs[key]['center'],geometry=old[key]['radius']))
        if self.last in (1,2,3,4) and len(changed)==1 and old[changed[0]]['color']==objs[changed[0]]['color']:
            key=changed[0];a,b=old[key]['center'],objs[key]['center'];delta=(b[0]-a[0],b[1]-a[1]);m=self.models.setdefault(self.last,dict(delta=delta,support=[]))
            if tuple(m['delta'])!=delta:self.models[self.last]=m=dict(delta=delta,support=[]);self.layout=None
            m['support'].append(dict(source=src,color=old[key]['color'],origin=a,destination=b,geometry=old[key]['radius']))
    def assignment(self,objs,models):
        all_targets=[(color,tuple(p)) for color,ps in sorted(self.targets.items()) for p in ps]
        if not all_targets or len(all_targets)>16:return None
        dy=[abs(m['delta'][0]) for m in models.values() if m['delta'][0]];dx=[abs(m['delta'][1]) for m in models.values() if m['delta'][1]];sy=min(dy) if dy else 1;sx=min(dx) if dx else 1;dp={0:(0,{},{})}
        for key,o in sorted(objs.items()):
            if key not in self.radii:return None
            cy,cx=o['center'];choices={(0,o['color']):(0,(cy,cx))}
            for y in range(cy%sy,62,sy):
                for x in range(cx%sx,64,sx):
                    pts=shape_points((y,x),self.radii[key])
                    for color in self.targets:
                        if not color_safe((y,x),self.radii[key],color,self.paint_sites,self.surface_margin):continue
                        mask=sum(1<<i for i,(c,p) in enumerate(all_targets) if c==color and p in pts)
                        if not mask:continue
                        cost=abs(y-cy)/sy+abs(x-cx)/sx+(8 if color!=o['color'] else 0);item=(mask,color)
                        if item not in choices or (cost,(y,x))<choices[item]:choices[item]=(cost,(y,x))
            nd={}
            for mask,(cost,layout,binding) in dp.items():
                for (add,color),(distance,center) in choices.items():
                    combined=mask|add;score=cost+distance
                    if combined not in nd or score<nd[combined][0]:nd[combined]=(score,dict(layout,**{key:center}),dict(binding,**{key:color}))
            dp=nd
        complete=(1<<len(all_targets))-1
        if complete not in dp:return None
        _,layout,self.object_target_colors=dp[complete];return layout
    def respond(self,obs):
        objs,targets=self.track.extract(obs);self.observe(obs,objs)
        if self.level!=obs['levels_completed']:
            self.level=obs['levels_completed'];self.targets=copy.deepcopy(targets);self.source=digest(obs);self.radii={k:o['radius'] for k,o in objs.items()};self.layout=None;self.calibrated=set();self.calibration=[];self.conversion_targets={};self.object_target_colors={};self.paint_sites=color_sites(obs);self.paint_source=digest(obs);self.target_evidence={(int(c),tuple(p)):digest(obs) for c,ps in self.targets.items() for p in ps};self.target_ring_colors={obs['frame'][p[0]-1][p[1]-1] for ps in self.targets.values() for p in ps}
        fresh=scene(obs)[1];expanded=False
        if obs['state']=='NOT_FINISHED':
            for c,ps in sorted(fresh.items()):
                for p in sorted(ps):
                    k=(int(c),tuple(p))
                    if k not in self.target_evidence and int(c)!=self.track.badge and tuple(p) not in {q for _,q in self.target_evidence} and obs['frame'][p[0]-1][p[1]-1] in self.target_ring_colors:
                        self.target_evidence[k]=digest(obs);self.targets.setdefault(int(c),[]).append(tuple(p));expanded=True
            if expanded:
                self.targets={c:sorted(set(map(tuple,ps))) for c,ps in self.targets.items()};self.layout=None;self.conversion_targets={}
        active=[k for k,o in objs.items() if o['selected']];action=None;cert=None;reason='unresolved_shared_shape_scene';models={a:m for a,m in self.models.items() if len({tuple(p['origin']) for p in m['support']})>=2}
        if obs['state']=='WIN':reason='WIN'
        elif obs['state']=='GAME_OVER':action=0;reason='reset_after_failure'
        elif len(active)==1 and all(k in objs for k in self.radii):
            key=active[0];o=objs[key];legal=sorted(set(obs['available_actions'])&{1,2,3,4})
            if key not in self.calibrated:
                if not self.calibration:self.calibration=[a for a in legal for _ in range(2)] if len(models)<len(legal) else [legal[0]]
                action=self.calibration.pop(0);reason='confirm_retained_object_controls'
                if not self.calibration:self.calibrated.add(key)
            else:
                if self.layout is None:self.layout=self.assignment(objs,models)
                site=None;goal=self.layout.get(key) if self.layout else None;target_color=self.object_target_colors.get(key)
                retained=self.conversion_targets.get(key)
                if retained and tuple(retained['goal'])==tuple(o['center']):self.conversion_targets.pop(key);retained=None
                if retained:
                    goal=retained['goal'];site=dict(retained['site'],context=digest(obs))
                elif goal and target_color!=o['color']:
                    sites=[]
                    for q in parts(obs['frame']):
                        if q['color']!=target_color or q['h']!=q['w'] or not(3<=q['h']<=8) or q['area']!=q['h']*q['w']:continue
                        dy=[abs(m['delta'][0]) for m in models.values() if m['delta'][0]];dx=[abs(m['delta'][1]) for m in models.values() if m['delta'][1]];sy=min(dy) if dy else 1;sx=min(dx) if dx else 1
                        cells=[(y,x) for y in range(q['y'],q['y']+q['h']) for x in range(q['x'],q['x']+q['w']) if (y-o['center'][0])%sy==0 and (x-o['center'][1])%sx==0]
                        for p in cells:sites.append((abs(p[0]-o['center'][0])+abs(p[1]-o['center'][1]),p,q))
                    if sites:
                        _,goal,q=min(sites,key=lambda a:(a[0],a[1]));site=dict(context=digest(obs),evidence_source=digest(obs),color=target_color,y=q['y'],x=q['x'],size=q['h'],interpretation='hypothesized_color_conversion_site');self.conversion_targets[key]=dict(goal=goal,site=copy.deepcopy(site))
                if goal and tuple(goal)!=tuple(o['center']):
                    queue=deque([(tuple(o['center']),[])]);seen={tuple(o['center'])};path=None
                    while queue and len(seen)<4096:
                        here,seq=queue.popleft()
                        if here==tuple(goal):path=seq;break
                        for a,m in sorted(models.items()):
                            ny,nx=here[0]+m['delta'][0],here[1]+m['delta'][1]
                            if 0<=ny<62 and 0<=nx<64 and (ny,nx) not in seen and (site is not None or target_color!=o['color'] or color_safe((ny,nx),self.radii[key],target_color,self.paint_sites,self.surface_margin)):seen.add((ny,nx));queue.append(((ny,nx),seq+[a]))
                    if path:
                        action=path[0];reason='test_color_conversion_site' if site else 'shared_color_coverage_plan';assigned=[] if site else [p for p in self.targets.get(target_color,[]) if tuple(p) in shape_points(goal,self.radii[key])]
                        cert=dict(kind='cross_coverage_plan',context=digest(obs),action=action,active_color=o['color'],target_color=target_color,target_object_bindings={t:[k for k,c in self.object_target_colors.items() if c==t] for t in self.targets},mapping_is_hypothesis=True,conversion_site=site,avoided_color_sites=[p for p in self.paint_sites if p['color']!=target_color] if site is None and target_color==o['color'] else [],color_site_source=self.paint_source,surface_margin=self.surface_margin,surface_evidence=copy.deepcopy(self.surface_evidence),color_change_evidence=copy.deepcopy(self.color_changes),active_shape=key,center=o['center'],radius=self.radii[key],targets=assigned,target_source=self.source,goal=goal,path=path,models={a:self.models[a] for a in set(path)},goal_is_hypothesis=True,transfer_hypothesis=True,retained_goal_outcomes=copy.deepcopy(self.goal_outcomes),shared_goal_assignment={k:dict(color=objs[k]['color'],geometry=self.radii[k],center=p) for k,p in self.layout.items()},all_targets=self.targets,target_ring_colors=sorted(self.target_ring_colors),temporal_targets=[dict(color=c,point=p,source=h) for (c,p),h in sorted(self.target_evidence.items())])
                if action is None and 5 in obs['available_actions']:action=5;reason='select_next_geometric_object'
        if action is None and obs['state']=='NOT_FINISHED':action=5 if 5 in obs['available_actions'] else min(obs['available_actions'])
        self.previous=copy.deepcopy(obs);self.last=action;self.track.commit(action,self.models.get(action,{}).get('delta'))
        return dict(action=action,data={},done=action is None,certificate=cert,advisor='shared_shape_coverage',diagnostics=dict(reason=reason,retained_transitions=len(self.history),goal_outcomes=copy.deepcopy(self.goal_outcomes),objects=objs,targets=self.targets,assignment=self.layout))
