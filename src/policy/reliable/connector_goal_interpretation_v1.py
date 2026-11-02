"""Revise contact into marker coincidence only from retained actual task feedback."""
import copy,heapq
from composite_connector_learner_v5 import Learner as Base,identity,rotate,ports,apply
from composite_connector_learner_v6 import hypotheses as contact_hypotheses
from visual_transform_learner import digest

def family(actor):
    signatures=[]
    for turn in range(4):
        for color,cells in ports(dict(actor,shape=rotate(actor['shape'],turn))).items():
            y=min(a for a,b in cells);x=min(b for a,b in cells);signatures.append(tuple(sorted((a-y,b-x) for a,b in cells)))
    return min(signatures) if signatures else ()
def coincidences(actor,others):
    out=[]
    for target in others:
        if identity(target)==identity(actor):continue
        for turn in range(4):
            shape=rotate(actor['shape'],turn)
            for color,cells in ports(dict(actor,shape=shape)).items():
                refs=ports(target).get(color)
                if not refs:continue
                oy=target['origin'][0]+min(y for y,x in refs)-min(y for y,x in cells);ox=target['origin'][1]+min(x for y,x in refs)-min(x for y,x in cells)
                ac={(y+oy,x+ox):c for y,x,c in shape};tc={(y+target['origin'][0],x+target['origin'][1]):c for y,x,c in target['shape']}
                ap={(y+oy,x+ox) for y,x in cells};tp={(y+target['origin'][0],x+target['origin'][1]) for y,x in refs}
                if ap!=tp or ac.keys()&tc.keys()!=ap or any(ac[q]!=color or tc[q]!=color for q in ap):continue
                out.append(dict(shape=shape,origin=(oy,ox),connector_color=color,target=target,interpretation='coincidence',scope='Literal matching marker positions; task role is an unconfirmed goal hypothesis.'))
    return out
class Learner(Base):
    def __init__(self):super().__init__();self.goal_outcomes=[];self.archive={};self.disable_goal_transfer=False
    def observe(self,raw,action=None):
        old=copy.deepcopy(self.previous);intent=copy.deepcopy(self.pending)
        super().observe(raw,action)
        if old is None or action is None:return
        row=dict(before=old,action=action,after=copy.deepcopy(raw));h=digest(row);self.archive[h]=row
        if not intent or len(intent['path'])!=1:return
        progress=raw['levels_completed']>old['levels_completed'] or raw['state']=='WIN'
        seen=self.scene(raw['frame']);goal=intent['goal'];at=any(o['shape']==goal['shape'] and o['origin']==goal['origin'] for o in seen)
        if progress or at:
            self.goal_outcomes.append(dict(source=h,level=old['levels_completed'],actor_identity=intent['actor_identity'],family=family(intent['actor']),interpretation=goal.get('interpretation','contact'),progress=progress,goal=copy.deepcopy(goal),intended_goal_is_hypothesis=True))
    def propose(self,obs):
        if obs['state']!='NOT_FINISHED':return None
        legal=sorted(set(obs['available_actions'])&{1,2,3,4,5,7});scene=self.scene(obs['frame']);plans=[]
        for actor in scene:
            ident=identity(actor);fam=family(actor)
            if not any(k==ident and m['changed'] and m['rules'] for (k,a),m in self.models.items()):continue
            evidence=[q for q in self.goal_outcomes if q['family']==fam]
            successes=[q for q in evidence if q['progress']]
            preference=successes[-1]['interpretation'] if successes and not self.disable_goal_transfer else 'contact'
            failed=[q for q in evidence if not q['progress'] and q['level']==obs['levels_completed'] and q['actor_identity']==ident]
            candidates=[dict(g,interpretation='contact') for g in contact_hypotheses(actor,scene)]
            if failed or preference=='coincidence':candidates+=coincidences(actor,scene)
            for goal in candidates:
                if (ident,goal['shape'],goal['origin']) in self.failed:continue
                def distance(p):return abs(p['origin'][0]-goal['origin'][0])+abs(p['origin'][1]-goal['origin'][1])+int(p['shape']!=goal['shape'])*4
                queue=[(distance(actor),0,0,actor,[])];seen=set();serial=0
                occupied={(y+o['origin'][0],x+o['origin'][1]):c for o in scene if identity(o)!=ident for y,x,c in o['shape']}
                while queue and len(seen)<768:
                    _,depth,_,here,path=heapq.heappop(queue);key=(here['shape'],here['origin'])
                    if key in seen:continue
                    seen.add(key)
                    if key==(goal['shape'],goal['origin']):
                        if path:plans.append((int(goal['interpretation']!=preference),len(path),distance(actor),actor,goal,path,evidence))
                        break
                    if depth>=80:continue
                    for action in legal:
                        modeled=self.model(here,action)
                        if modeled is None:continue
                        predicted,m=modeled
                        if predicted==here:continue
                        cells={(y+predicted['origin'][0],x+predicted['origin'][1]):c for y,x,c in predicted['shape']}
                        if any(not(0<y<63 and 0<x<63) for y,x in cells):continue
                        overlap=cells.keys()&occupied.keys()
                        if overlap and (goal['interpretation']!='coincidence' or any(cells[q]!=goal['connector_color'] or occupied[q]!=goal['connector_color'] for q in overlap)):continue
                        if goal['interpretation']=='contact' and (predicted['shape'],predicted['origin'])!=(goal['shape'],goal['origin']) and any((y+dy,x+dx) in occupied for y,x in cells for dy,dx in ((1,0),(-1,0),(0,1),(0,-1))):continue
                        serial+=1;edge=dict(action=action,predicted=predicted,rules=sorted(m['rules']),support=sorted(set(m['support'])))
                        heapq.heappush(queue,(depth+1+distance(predicted),depth+1,serial,predicted,path+[edge]))
        if not plans:return None
        _,_,_,actor,goal,path,evidence=min(plans,key=lambda p:(p[:3],p[3]['origin'],p[4]['origin']))
        return dict(action=path[0]['action'],data={},kind='revisable_connector_goal_plan',actor=actor,actor_identity=identity(actor),goal=goal,path=path,context=digest(obs),goal_evidence=copy.deepcopy(evidence),goal_outcomes=copy.deepcopy(self.goal_outcomes))
