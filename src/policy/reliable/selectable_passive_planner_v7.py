"""Learn a contact effect, retain literal shape goals, and replan after mismatches."""
import copy
from selectable_passive_contact_learner_v3 import Agent as Base
from visible_passive_components_v1 import components
from passive_shape_geometry_v1 import enclosed,mask
from passive_macro_planner_v3 import search
class Agent(Base):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.shape_goals=[];self.passive_planning=False;self.passive_plan=[];self.passive_objects=[];self.passive_pending=None;self.passive_trials=[];self.passive_model=None;self.passive_searches=[];self.passive_model_candidates=[]
    def reset_level(self,raw):
        super().reset_level(raw);self.shape_goals=[];self.passive_planning=False;self.passive_plan=[];self.passive_objects=[];self.passive_pending=None;self.passive_trials=[];self.passive_model=None;self.passive_searches=[];self.passive_model_candidates=[]
    def observe(self,raw):
        r=super().observe(raw)
        if len(self.objects)==1:
            shapes={tuple(map(tuple,q['shape'])) for q in self.candidates(raw)}
            for outline in components(raw['frame']):
                if outline['ink'] not in {g['ink'] for g in self.goals}:continue
                inside=enclosed(outline)
                if inside and tuple(inside['shape']) in shapes and not any(g['interior']['box']==inside['box'] for g in self.shape_goals):self.shape_goals.append(dict(outline=copy.deepcopy(outline),interior=inside,observed_at=self.t,goal_is_hypothesis=True))
        return r
    def allowed(self):return set(self.passive_terrain_memory)|{self.floor}|{g['ink'] for g in self.goals}
    def predict(self,raw,body,objects,action):
        dy,dx=self.motions[action]['delta'];h,w=body['box'][2:];actor=tuple(body['box'][:2]);target=(actor[0]+dy,actor[1]+dx);actor_shape=tuple((a,b) for a in range(h) for b in range(w));actor_mask=mask(actor,actor_shape);original=actor_mask;positions=[tuple(q['box'][:2]) for q in objects];shapes=[tuple(map(tuple,q['shape'])) for q in objects];masks=[mask(p,s) for p,s in zip(positions,shapes)]
        for v in masks:original|=v
        def valid(p,s,obstacles=0):
            if min(p)<0 or p[0]+max(a for a,b in s)>=64 or p[1]+max(b for a,b in s)>=64:return False
            return not mask(p,s)&obstacles and all(raw['frame'][p[0]+a][p[1]+b] in self.allowed() or (original>>((p[0]+a)*64+p[1]+b))&1 for a,b in s)
        if not valid(target,actor_shape):return actor,tuple(positions)
        tm=mask(target,actor_shape);hit=[i for i,v in enumerate(masks) if tm&v]
        if not hit:return target,tuple(positions)
        if len(hit)!=1:return actor,tuple(positions)
        i=hit[0];obstacles=actor_mask
        for j,v in enumerate(masks):
            if i!=j:obstacles|=v
        p=positions[i]
        for _ in range(64):
            q=(p[0]+dy,p[1]+dx)
            if not valid(q,shapes[i],obstacles):break
            p=q
            if self.passive_model=='step' or self.passive_model.startswith('fixed:') and _+1>=int(self.passive_model.split(':')[1]):break
        positions[i]=p;return actor,tuple(positions)
    def recover(self,raw,old,expected):
        result=[]
        for i,o in enumerate(old):
            ps=[tuple(expected[i]),tuple(o['box'][:2])];ps+= [tuple(q['box'][:2]) for q in self.candidates(raw) if q['ink']==o['ink'] and q['shape']==o['shape']]
            found=[]
            for p in dict.fromkeys(ps):
                if all(0<=p[0]+a<64 and 0<=p[1]+b<64 and raw['frame'][p[0]+a][p[1]+b]==o['ink'] for a,b in o['shape']):found.append(p)
            if not found:return []
            p=found[0];q=copy.deepcopy(o);q['box']=(*p,*o['box'][2:]);result.append(q)
        if len({tuple(o['box']) for o in result})!=len(result):return []
        return result
    def respond(self,raw):
        if self.level!=raw['levels_completed'] or raw['state']!='NOT_FINISHED' or not self.passive_planning:
            r=super().respond(raw)
            if not r['done'] or raw['state']!='NOT_FINISHED' or len(self.objects)!=1 or not self.learned_passive_effects:return r
            effect=self.learned_passive_effects[-1];m=self.motions.get(effect['action'])
            if not m or not effect['actor_after']:return r
            self.passive_model='step' if tuple(effect['delta'])==tuple(m['delta']) else 'slide'
            distance=sum(abs(v) for v in effect['delta']);unit=sum(abs(v) for v in m['delta']);self.passive_model_candidates=[self.passive_model]+(['fixed:'+str(distance//unit)] if unit and distance>unit and distance%unit==0 else [])
            self.passive_objects=[q for q in self.candidates(raw) if q['ink']==effect['after']['ink'] and q['shape']==effect['after']['shape']]
            if not self.passive_objects:return r
            self.passive_planning=True
        else:self.observe(raw)
        if self.passive_pending:
            p=self.passive_pending;current=self.recover(raw,p['objects'],p['predicted_objects']);actual_actor=tuple(self.objects[0]['box'][:2]) if len(self.objects)==1 else None
            confirmed=bool(current) and actual_actor==tuple(p['predicted_actor']) and tuple(tuple(q['box'][:2]) for q in current)==tuple(p['predicted_objects'])
            self.passive_trials.append(dict(source=p['source'],action=p['action'],objects_before=p['objects'],objects_after=copy.deepcopy(current),actor_before=p['actor'],actor_after=copy.deepcopy(self.objects[0]) if len(self.objects)==1 else None,predicted_actor=p['predicted_actor'],predicted_objects=p['predicted_objects'],prediction_confirmed=confirmed,model=p['model'],model_is_hypothesis=True))
            if not confirmed:self.passive_plan=[]
            self.passive_objects=current;self.passive_pending=None
        if len(self.objects)!=1 or not self.passive_objects:return self.terminal()
        if not self.passive_plan:
            forbidden={(tuple(tuple(q['box'][:2]) for q in p['objects_before']),tuple(p['actor_before']['box'][:2]),p['action']) for p in self.passive_trials if not p['prediction_confirmed']}
            if len(self.passive_searches)>=12:return self.terminal()
            scene=dict(raw,_actor_goals=self.goals);p=None
            contradicted={t['model'] for t in self.passive_trials if not t['prediction_confirmed'] and any(tuple(q['box'][:2])!=tuple(pos) for q,pos in zip(t['objects_before'],t['predicted_objects']))}
            candidates=[self.passive_model]+[m for m in self.passive_model_candidates if m!=self.passive_model]
            for model in candidates:
                if model in contradicted:continue
                p=search(scene,self.objects[0],self.passive_objects,self.shape_goals,self.motions,self.allowed(),model,forbidden=forbidden)
                self.passive_searches.append(dict(source=self.t,found=p is not None,expanded=p['expanded'] if p else None,model=model))
                if p and p['actions']:self.passive_model=model;break
            if not p or not p['actions']:return self.terminal()
            self.passive_plan=p['actions']
        a=self.passive_plan.pop(0);actor,positions=self.predict(raw,self.objects[0],self.passive_objects,a);body=self.objects[0]
        self.passive_pending=dict(source=self.t,action=a,actor=copy.deepcopy(body),objects=copy.deepcopy(self.passive_objects),predicted_actor=actor,predicted_objects=positions,model=self.passive_model)
        r=self.answer(raw,a,{},'execute_passive_shape_plan',body,[a]+self.passive_plan)
        r['certificate']['passive_plan_hypothesis']=dict(objects=copy.deepcopy(self.passive_objects),goals=copy.deepcopy(self.shape_goals),effects=copy.deepcopy(self.learned_passive_effects),trials=copy.deepcopy(self.passive_trials),model=self.passive_model,predicted_actor=actor,predicted_objects=positions,model_is_hypothesis=True)
        return r
    def terminal(self):return dict(done=True,action=None,data={},learned_passive_effects=copy.deepcopy(self.learned_passive_effects),passive_trials=copy.deepcopy(self.passive_trials),passive_searches=copy.deepcopy(self.passive_searches))
