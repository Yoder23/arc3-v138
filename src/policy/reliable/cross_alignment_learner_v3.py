"""Learn selected-object controls and test color-matched cross coverage goals."""
from collections import Counter,deque
import copy
from visual_transform_learner import digest

from cross_shape_geometry_v1 import scene,covers

class Agent:
    def __init__(self):
        self.level=None;self.previous=None;self.last=None;self.history={};self.models={};self.radii={};self.targets={};self.switch_sources=[];self.goal_outcomes=[];self.trials=Counter();self.failed=set();self.pending=None;self.seen_colors=set();self.calibration=[];self.calibrated=set();self.visits=Counter();self.target_source=None
    def observe(self,obs,objs):
        if self.previous is None or self.last is None:return
        e=dict(before=self.previous,action=self.last,data={},after=copy.deepcopy(obs));src=digest(e);self.history[src]=e;old,_=scene(self.previous)
        if obs['levels_completed']!=self.previous['levels_completed'] or obs['state']=='WIN':
            self.goal_outcomes.append(dict(source=src,progress=True,goal='color_matched_cross_coverage'));return
        changed=[c for c in old.keys()&objs.keys() if old[c]['center']!=objs[c]['center']]
        if self.last in (1,2,3,4) and len(changed)==1:
            c=changed[0];a,b=old[c]['center'],objs[c]['center'];delta=b[0]-a[0],b[1]-a[1]
            selected=[k for k,o in old.items() if o['selected']]
            if selected!=[c]:return
            m=self.models.setdefault(self.last,dict(delta=delta,support=[]))
            if m['delta']!=delta:self.models[self.last]=m=dict(delta=delta,support=[])
            m['support'].append(dict(source=src,color=c,origin=a,destination=b,geometry=old[c]['radius']));self.seen_colors.add(c)
        if self.last==5 and not changed and set(old)==set(objs) and {c for c in old if old[c]['selected']}!={c for c in objs if objs[c]['selected']}:self.switch_sources.append(src)
        if self.pending and all(c in objs and covers(objs[c]['center'],self.radii[c],self.targets.get(c,[])) for c in self.targets):
            self.goal_outcomes.append(dict(source=src,progress=False,goal='color_matched_cross_coverage',configuration={c:o['center'] for c,o in objs.items()}))
        self.pending=None
    def respond(self,obs):
        objs,targets=scene(obs);self.observe(obs,objs)
        if self.level!=obs['levels_completed']:
            self.level=obs['levels_completed'];self.target_source=digest(obs);self.targets={c:ps for c,ps in targets.items() if ps};self.radii={c:o['radius'] for c,o in objs.items()};self.calibration=[];self.calibrated=set();self.visits.clear()
        for c,o in objs.items():
            self.radii.setdefault(c,o['radius'])
        action=None;cert=None;reason='unresolved_cross_scene';selected=[c for c,o in objs.items() if o['selected']]
        if obs['state']=='WIN':reason='WIN'
        elif obs['state']=='GAME_OVER':action=0;reason='reset_after_failure'
        elif len(selected)==1 and self.targets and set(self.targets)<=set(objs):
            active=selected[0];here=objs[active]['center'];legal=sorted(set(obs['available_actions'])&{1,2,3,4});models={a:m for a,m in self.models.items() if len({tuple(p['origin']) for p in m['support']})>=2}
            if active not in self.calibrated:
                if not self.calibration:self.calibration=[a for a in legal for _ in range(2)] if len(models)<len(legal) else [legal[0]]
                action=self.calibration.pop(0);reason='learn_selected_cross_controls'
                if not self.calibration:self.calibrated.add(active)
            elif active in self.targets and not covers(here,self.radii[active],self.targets[active]) and models:
                goals=[(y,x) for y in range(0,62) for x in range(0,64) if covers((y,x),self.radii[active],self.targets[active])]
                queue=deque([(here,[])]);seen={here};path=None;goal=None
                while queue and len(seen)<4096:
                    pos,seq=queue.popleft()
                    if pos in goals:path=seq;goal=pos;break
                    for a,m in sorted(models.items()):
                        dy,dx=m['delta'];n=(pos[0]+dy,pos[1]+dx)
                        if 0<=n[0]<62 and 0<=n[1]<64 and n not in seen:seen.add(n);queue.append((n,seq+[a]))
                if path:
                    action=path[0];reason='cross_coverage_goal';cert=dict(kind='cross_coverage_plan',context=digest(obs),action=action,active_color=active,center=here,radius=self.radii[active],targets=self.targets[active],target_source=self.target_source,goal=goal,path=path,models={a:self.models[a] for a in set(path)},goal_is_hypothesis=True,transfer_hypothesis=True,retained_goal_outcomes=copy.deepcopy(self.goal_outcomes));self.pending=cert
            if action is None and 5 in obs['available_actions']:action=5;reason='change_selected_cross'
        if action is None and obs['state']=='NOT_FINISHED':
            legal=sorted(set(obs['available_actions'])&{1,2,3,4,5});action=legal[len(self.history)%len(legal)] if legal else None
        self.previous=copy.deepcopy(obs);self.last=action
        return dict(action=action,data={},done=action is None,certificate=cert,advisor='cross_alignment_learner',diagnostics=dict(reason=reason,retained_transitions=len(self.history),goal_outcomes=copy.deepcopy(self.goal_outcomes),switch_evidence=self.switch_sources[-4:],targets=self.targets,centers={c:o['center'] for c,o in objs.items()}))
