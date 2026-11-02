"""Retrieve observed contact ranges, choose a reachable controller, then restore other goals."""
import copy
from selectable_multi_passive_inquiry_v4 import Agent as Base
from selectable_passive_planner_v9 import Agent as Ordinary
from passive_macro_planner_v3 import search
class Agent(Base):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.handoff=None;self.handoff_completed=False;self.handoff_searches=[];self.handoff_pending=None
    def reset_level(self,raw):
        super().reset_level(raw);self.handoff=None;self.handoff_completed=False;self.handoff_searches=[];self.handoff_pending=None
    def range_hypotheses(self,objects):
        models={}
        for effect in self.learned_passive_effects:
            if not any(tuple(map(tuple,q['shape']))==tuple(map(tuple,effect['after']['shape'])) for q in objects):continue
            choices=[m for m in self.motion_memory if m['action']==effect['action'] and m['source']<effect['source']]
            if not choices:continue
            motion=max(choices,key=lambda m:m['source']);unit=sum(abs(v) for v in motion['delta']);distance=sum(abs(v) for v in effect['delta'])
            if unit and distance%unit==0:
                n=distance//unit
                if 1<=n<=64:models.setdefault('step' if n==1 else 'fixed:'+str(n),effect['source'])
        return sorted(models,key=lambda m:(1 if m=='step' else int(m.split(':')[1])))+['slide']
    def make_handoff(self,raw,objects):
        if len(self.handoff_searches)>=12:return None
        forbidden={(tuple(tuple(q['box'][:2]) for q in p['objects_before']),tuple(p['actor_before']['box'][:2]),p['action']) for p in self.passive_trials if not p['prediction_confirmed']};scene=dict(raw,_actor_goals=self.goals);choices=[]
        for model in self.range_hypotheses(objects):
            for body in self.objects:
                plan=search(scene,body,objects,self.shape_goals,self.motions,self.allowed(),model,max_expansions=2000,forbidden=forbidden)
                ident=self.identities[tuple(body['box'])];self.handoff_searches.append(dict(source=self.t,controller=ident,model=model,found=plan is not None,expanded=plan['expanded'] if plan else None))
                if plan and plan['actions']:choices.append((len(plan['actions'])+int(tuple(body['box'])!=tuple(self.active_box or ())),model,ident,plan))
            if choices:break
        if not choices:return None
        _,model,ident,plan=min(choices,key=lambda c:c[:3]);return dict(controller=ident,model=model,actions=plan['actions'],objects=copy.deepcopy(objects),selections=0)
    def passive_satisfied(self,objects):
        return bool(objects) and all(any(tuple(q['box'])==tuple(g['interior']['box']) and tuple(map(tuple,q['shape']))==tuple(map(tuple,g['interior']['shape'])) for g in self.shape_goals) for q in objects)
    def respond(self,raw):
        if self.handoff_completed and self.level==raw['levels_completed']:return Ordinary.respond(self,raw)
        if self.handoff is None or self.level!=raw['levels_completed'] or raw['state']!='NOT_FINISHED':
            r=super().respond(raw)
            if not r['done'] or raw['state']!='NOT_FINISHED' or len(self.objects)<2 or not self.learned_passive_effects:return r
            shapes={tuple(map(tuple,e['after']['shape'])) for e in self.learned_passive_effects};objects=[q for q in self.candidates(raw) if tuple(map(tuple,q['shape'])) in shapes]
            self.handoff=self.make_handoff(raw,objects)
            if self.handoff is None:return self.handoff_terminal()
        else:self.observe(raw)
        state=self.handoff
        if self.handoff_pending:
            p=self.handoff_pending;current=self.recover(raw,p['objects'],p['predicted_objects']);body=next((b for b in self.objects if self.identities.get(tuple(b['box']))==p['controller']),None)
            actual_actor=tuple(body['box'][:2]) if body else None;confirmed=bool(current) and actual_actor==tuple(p['predicted_actor']) and tuple(tuple(q['box'][:2]) for q in current)==tuple(p['predicted_objects'])
            self.passive_trials.append(dict(source=p['source'],action=p['action'],objects_before=p['objects'],objects_after=copy.deepcopy(current),actor_before=p['actor'],actor_after=copy.deepcopy(body),predicted_actor=p['predicted_actor'],predicted_objects=p['predicted_objects'],prediction_confirmed=confirmed,model=p['model'],model_is_hypothesis=True))
            if body and tuple(body['box'])==tuple(p['actor']['box']):
                for before,after in zip(p['objects'],current):
                    delta=tuple(after['box'][i]-before['box'][i] for i in (0,1))
                    if (delta[0]==0)!=(delta[1]==0):self.learned_passive_effects.append(dict(source=p['source'],action=p['action'],before=before,after=copy.deepcopy(after),delta=delta,actor_before=p['actor'],actor_after=copy.deepcopy(body),outcome='observed_other_component_translation',causality_is_hypothesis=True))
            state['objects']=current;self.handoff_pending=None
            if not confirmed:state['actions']=[]
        if not state['objects']:return self.handoff_terminal()
        if not state['actions']:
            if self.passive_satisfied(state['objects']):
                self.handoff=None;self.multi_passive_probe=None;self.handoff_completed=True;return Ordinary.respond(self,raw)
            self.handoff=self.make_handoff(raw,state['objects'])
            if self.handoff is None:return self.handoff_terminal()
            state=self.handoff
        body=next((b for b in self.objects if self.identities.get(tuple(b['box']))==state['controller']),None)
        if not body:return self.handoff_terminal()
        self.passive_model=state['model']
        if tuple(body['box'])!=tuple(self.active_box or ()):
            if state['selections']>=4:return self.handoff_terminal()
            state['selections']+=1;y,x,h,w=body['box'];r=self.answer(raw,6,dict(x=x+w//2,y=y+h//2),'select_passive_handoff_controller',body,state['actions'])
        else:
            a=state['actions'].pop(0);actor,positions=self.predict(raw,body,state['objects'],a);self.handoff_pending=dict(source=self.t,action=a,controller=state['controller'],actor=copy.deepcopy(body),objects=copy.deepcopy(state['objects']),predicted_actor=actor,predicted_objects=positions,model=state['model']);r=self.answer(raw,a,{},'execute_controller_handoff_plan',body,[a]+state['actions'])
        if not r['done']:r['certificate']['passive_plan_hypothesis']=dict(objects=copy.deepcopy(state['objects']),goals=copy.deepcopy(self.shape_goals),effects=copy.deepcopy(self.learned_passive_effects),trials=copy.deepcopy(self.passive_trials),model=state['model'],model_is_hypothesis=True)
        return r
    def handoff_terminal(self):return dict(done=True,action=None,data={},learned_passive_effects=copy.deepcopy(self.learned_passive_effects),passive_trials=copy.deepcopy(self.passive_trials),handoff_searches=copy.deepcopy(self.handoff_searches))
