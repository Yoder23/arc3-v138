"""Use a jointly checked intermediate-action hypothesis when simple obstacle parking fails."""
import copy
from coupled_navigation_manipulation_v2 import Agent as Prior
from coupled_navigation_core_v10 import Agent as Core,actors
from coupled_joint_relocation_v2 import search
from visual_transform_learner import digest
class Agent(Prior):
    def __init__(self):
        super().__init__();self.joint=None;self.joint_outcomes=[];self.joint_roots=set()
    def relocate(self,obs,m,origin):
        choice,info=super().relocate(obs,m,origin)
        if info.get('reason') not in ('no_supported_parking_route','relaxed_goal_unreachable') or digest(obs) in self.joint_roots:return choice,info
        self.joint_roots.add(digest(obs));effects,proof=self.controls();floor=self.floor_counts.most_common(1)[0][0];m['hazard_colors']=sorted(self.hazards);path,diagnostic=search(obs,m,floor,effects)
        if not path:return choice,dict(**info,joint_search=diagnostic)
        first=path[0];self.joint=dict(root=digest(obs),selection_source=m['source'],level=self.level,signature=m['signature'],inactive=m['inactive'],shape=m['shape'],marker_color=m['marker_color'],selected_color=m['selected_color'],pending=copy.deepcopy(path[1:]),expected=copy.deepcopy(first),issued=1,actual_outcomes=[],planned_actions=len(path),model_support=proof,object_observations=copy.deepcopy(m['observations']))
        result=('release',None) if first['kind']=='select_actors' else ('move',(first['action'],first['marker']))
        return result,dict(reason='joint_actor_obstacle_hypothesis',planned_actions=len(path),**diagnostic)
    def close_joint(self,obs,matched,progress):
        self.joint_outcomes.append(dict(**self.joint,outcome=digest(obs),matched=matched,progress=progress));self.joint=None
        if self.manipulation:self.manipulation_memories.append(dict(**self.manipulation,outcome=digest(obs),joint=True,progress=progress));self.manipulation=None
    def respond(self,obs):
        if self.joint:
            j=self.joint;expected=j['expected'];progress=obs['levels_completed']>j['level'] or obs['state']=='WIN'
            color=j['inactive'] if expected['mode'] else j['signature'][0];_,pos=actors(obs['frame'],(color,j['signature'][1]));marker_color=j['selected_color'] if expected['mode'] else j['marker_color'];y,x=expected['marker'];matched=bool(pos) and sorted(pos)==sorted(map(tuple,expected['positions'])) and all(obs['frame'][y+a][x+b]==marker_color for a,b in j['shape'])
            source=digest(dict(before=self.previous,action=self.last,data=self.last_data,after=obs));j['actual_outcomes'].append(dict(source=source,expected=copy.deepcopy(expected),matched=matched,progress=progress))
            if progress or obs['state']!='NOT_FINISHED' or not matched or not j['pending']:
                self.close_joint(obs,matched,progress);response=Core.respond(self,obs)
            else:
                response=Core.respond(self,obs);step=j['pending'].pop(0);j['expected']=copy.deepcopy(step);j['issued']+=1;self.last=step['action'];self.last_data=copy.deepcopy(step['data']);self.predicted=None;response.update(action=step['action'],data=step['data'],done=False,certificate=None);response['diagnostics'].update(reason='joint_actor_obstacle_hypothesis',joint_root=j['root'],joint_issued=j['issued'],joint_remaining=len(j['pending']),forecast_is_hypothesis=True)
        else:response=super().respond(obs)
        response['diagnostics'].update(joint_active=bool(self.joint),joint_outcomes=len(self.joint_outcomes));return response
