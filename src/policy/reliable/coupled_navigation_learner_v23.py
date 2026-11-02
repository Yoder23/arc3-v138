"""Compose learned pressure conditions with actor/obstacle intermediate-action planning."""
import copy
from coupled_navigation_learner_v21 import Agent as Prior
from coupled_joint_relocation_v3 import search
from visual_transform_learner import digest
class Agent(Prior):
    def __init__(self):super().__init__();self.composed_roots=set();self.composed_plans=0
    def relocate(self,obs,m,origin):
        models=self.pressure_models.get(self.level,{});roles=self.pressure_roles.get(self.level,{})
        if models and self.floor_counts:
            effects,proof=self.controls();key=digest(dict(frame=obs['frame'][1:63],hazards=sorted(self.hazards),effects=effects))
            if key not in self.composed_roots:
                self.composed_roots.add(key);surface=dict(roles=copy.deepcopy(list(roles.values())),models=copy.deepcopy(list(models.values())),button_passability_is_hypothesis=True,pressure_condition_is_hypothesis=True);trial=copy.deepcopy(m);trial['hazard_colors']=sorted(self.hazards);trial['pressure_surface']=surface;floor=self.floor_counts.most_common(1)[0][0];path,diagnostic=search(obs,trial,floor,effects)
                if path:
                    first=path[0];self.composed_plans+=1;self.joint=dict(root=digest(obs),selection_source=m['source'],level=self.level,signature=m['signature'],inactive=m['inactive'],shape=m['shape'],marker_color=m['marker_color'],selected_color=m['selected_color'],pending=copy.deepcopy(path[1:]),expected=copy.deepcopy(first),issued=1,actual_outcomes=[],planned_actions=len(path),model_support=proof,object_observations=copy.deepcopy(m['observations']),pressure_surface=surface)
                    choice=('release',None) if first['kind']=='select_actors' else ('move',(first['action'],first['marker']))
                    return choice,dict(reason='joint_pressure_obstacle_hypothesis',planned_actions=len(path),**diagnostic)
        return super().relocate(obs,m,origin)
    def respond(self,obs):
        response=super().respond(obs)
        if self.joint and self.joint.get('pressure_surface') and 'plan_certificate' in self.joint:
            j=self.joint
            if not j.get('certificate_frozen'):
                b=copy.deepcopy(j['plan_certificate']);b['pressure_surface']=copy.deepcopy(j['pressure_surface']);j['plan_certificate']=b;j['plan_id']=digest(b);j['certificate_frozen']=True
            b=j['plan_certificate'];c=response['certificate'];c['plan_id']=j['plan_id']
            if 'plan' in c:c['plan']=copy.deepcopy(b)
        response['diagnostics']['composed_plans']=self.composed_plans;return response
