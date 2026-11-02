"""Learn remote pressure effects and plan through their occupancy-dependent state."""
import copy
from coupled_navigation_learner_v20 import Agent as Prior
from coupled_navigation_core_v10 import actors,cells
from coupled_pressure_model_v1 import roles,search
from visual_transform_learner import digest
class Agent(Prior):
    def __init__(self):super().__init__();self.pressure_roles={};self.pressure_models={};self.pressure_failures=[]
    def pressure_observe(self,obs):
        if not self.signature or self.level!=obs['levels_completed'] or not self.floor_counts:return
        level=self.level;color,size=self.signature;floor=self.floor_counts.most_common(1)[0][0];memory=self.pressure_roles.setdefault(level,{});models=self.pressure_models.setdefault(level,{})
        for c,r in roles(obs,size,floor,color).items():
            if c not in memory:memory[c]=r
        if not self.previous or self.last not in (1,2,3,4,7) or self.previous['levels_completed']!=level:return
        _,before=actors(self.previous['frame'],self.signature);_,after=actors(obs['frame'],self.signature)
        if not before or not after:return
        source=digest(dict(before=self.previous,action=self.last,data=self.last_data,after=obs));occupied=cells(before,size)|cells(after,size)
        for c,r in memory.items():
            opened={(y,x) for y in range(1,63) for x in range(64) if self.previous['frame'][y][x]==c and obs['frame'][y][x]==floor and (y,x) not in occupied}
            trigger=next((p for p in after if p not in before and all(self.previous['frame'][y][x]==c for y,x in cells([p],size))),None)
            if trigger and opened and opened==set(map(tuple,r['gates'])):
                m=models.setdefault(c,dict(color=c,gates=r['gates'],opening=[],closing=[],hypothesis='gate_open_while_matching_tile_occupied'));e=dict(source=source,button=trigger)
                if e not in m['opening']:m['opening'].append(e)
            if c in models:
                closed={(y,x) for y in range(1,63) for x in range(64) if self.previous['frame'][y][x]==floor and obs['frame'][y][x]==c and (y,x) not in occupied}
                if closed==set(map(tuple,models[c]['gates'])) and any(tuple(p) in before for p in r['buttons']) and not any(tuple(p) in after for p in r['buttons']):
                    if source not in models[c]['closing']:models[c]['closing'].append(source)
    def plan(self,obs,pos):
        memory=self.pressure_roles.get(self.level,{});controls,proof=self.controls()
        if not memory or len(controls)<4 or not self.floor_counts:return super().plan(obs,pos)
        floor=self.floor_counts.most_common(1)[0][0];models=self.pressure_models.get(self.level,{});path,goal=search(obs,pos,self.signature[1],floor,controls,memory,models,self.hazards)
        if path:return path,dict(floor=floor,effects=controls,support=proof,expanded=goal['expanded'],landmark_hypotheses=[],conditional_surface_model=dict(roles=copy.deepcopy(list(memory.values())),models=copy.deepcopy(list(models.values())),goal=goal,button_passability_is_hypothesis=True,pressure_condition_is_hypothesis=True))
        return None,dict(expanded=goal['expanded'])
    def respond(self,obs):
        self.pressure_observe(obs);response=super().respond(obs);c=response.get('certificate')
        if c and c.get('conditional_surface_model'):
            c['kind']='conditional_pressure_plan';c['hypothesis']=c['conditional_surface_model']['goal']['kind']
        response['diagnostics'].update(pressure_roles=len(self.pressure_roles.get(self.level,{})),pressure_models=len(self.pressure_models.get(self.level,{})));return response
