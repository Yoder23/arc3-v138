"""Goal revision followed by observed selection, feedback-stable identity, and assembly planning."""
from collections import Counter
import copy,heapq
from connector_goal_interpretation_v1 import Learner as GoalLearner
from connector_assembly_geometry_v1 import initial,locate,solve,valid,absolute,complete
from composite_connector_learner_v5 import rotate,apply,center2
from visual_transform_learner import digest
from structured_interaction_probe_v1 import parts

def pose(obj):return obj['shape'],obj['origin']
class Agent:
    def __init__(self):
        self.goal=GoalLearner();self.templates=[];self.level=None;self.layout=None;self.layout_diagnostics={};self.models={};self.selected=None;self.previous=None;self.before_pieces=None;self.last=None;self.history={};self.outcomes=[];self.trials=Counter();self.selection_sources=[];self.refutations=[];self.active=False;self.schedule=None;self.schedule_nodes=0;self.inquiries={};self.inquiry_actions=[]
    def learning(self,obs,pieces):
        if self.previous is None or self.last is None:return
        action,data=self.last;row=dict(before=self.previous,action=action,data=data,after=copy.deepcopy(obs));h=digest(row);self.history[h]=row
        if not self.before_pieces or not pieces or any(p is None for p in self.before_pieces+pieces):return
        if len(pieces)!=len(self.before_pieces) or self.previous['levels_completed']!=obs['levels_completed']:return
        changed=[i for i,(a,b) in enumerate(zip(self.before_pieces,pieces)) if pose(a)!=pose(b)]
        if action in (1,2,3,4,5,7) and len(changed)==1:
            i=changed[0];a=self.before_pieces[i];b=pieces[i];self.selected=i;rules=set()
            for t in range(4):
                if rotate(a['shape'],t)!=b['shape']:continue
                ca,cb=center2(a),center2(b);rules.add(('center2',t,cb[0]-ca[0],cb[1]-ca[1]));rules.add(('origin2',t,2*(b['origin'][0]-a['origin'][0]),2*(b['origin'][1]-a['origin'][1])))
            m=self.models.get(action)
            if m and not m['rules']&rules:self.refutations.append(dict(source=h,action=action,rejected=sorted(m['rules'])));m=None
            if m is None:m=dict(rules=rules,support=[],origins=set());self.models[action]=m
            m['rules']&=rules;m['support'].append(dict(source=h,before=a,after=b,piece=i));m['origins'].add(pose(a))
        if action==6:
            hit=[i for i,o in enumerate(self.before_pieces) if absolute(o).get((data.get('y'),data.get('x')))==1]
            if len(hit)==1 and not changed:
                i=hit[0]
                if pieces[i]['body_color']!=self.before_pieces[i]['body_color'] or self.selected==i:self.selected=i;self.selection_sources.append(dict(source=h,piece=i,before=self.before_pieces,after=pieces))
        self.outcomes.append(dict(source=h,level=obs['levels_completed'],matched_geometry=all(pose(pieces[i])==pose(g) for i,g in self.layout.items()) if self.layout else False,progress=obs['levels_completed']>self.previous['levels_completed'] or obs['state']=='WIN'))
    def model(self,obj,action):
        m=self.models.get(action)
        if not m or len(m['origins'])<2 or not m['rules']:return None
        candidates=[apply(obj,r) for r in sorted(m['rules'])]
        if any(c is None for c in candidates) or len({pose(c) for c in candidates})!=1:return None
        return candidates[0]
    def path(self,index,pieces,goal,legal):
        start=pieces[index];queue=[(0,0,0,start,[])];seen=set();serial=0
        def distance(o):return (abs(o['origin'][0]-goal['origin'][0])+abs(o['origin'][1]-goal['origin'][1]))/3+2*(o['shape']!=goal['shape'])
        while queue and len(seen)<1600:
            _,depth,_,here,path=heapq.heappop(queue);key=pose(here)
            if key in seen:continue
            seen.add(key)
            if key==pose(goal):return path
            if depth>=100:continue
            for action in legal:
                predicted=self.model(here,action)
                if predicted is None or pose(predicted)==key:continue
                if not valid([predicted]+[q for i,q in enumerate(pieces) if i!=index]):continue
                serial+=1;heapq.heappush(queue,(depth+1+distance(predicted),depth+1,serial,predicted,path+[(action,predicted)]))
        return None
    def order(self,pieces,legal):
        self.schedule_nodes=0;seen=set()
        def search(state):
            self.schedule_nodes+=1
            if self.schedule_nodes>48:return None
            pending=[i for i,g in self.layout.items() if pose(state[i])!=pose(g)]
            if not pending:return []
            key=tuple(pose(o) for o in state)
            if key in seen:return None
            seen.add(key)
            pending.sort(key=lambda i:abs(state[i]['origin'][0]-self.layout[i]['origin'][0])+abs(state[i]['origin'][1]-self.layout[i]['origin'][1]))
            for i in pending:
                path=self.path(i,state,self.layout[i],legal)
                if not path:continue
                trial=list(state);trial[i]=path[-1][1];tail=search(trial)
                if tail is not None:return [i]+tail
            return None
        return search(pieces)
    def respond(self,obs):
        raw=copy.deepcopy(obs);scene=initial(obs['frame'])
        if self.active and self.layout is None and len(scene)>len(self.templates):self.level=None
        pieces=locate(obs['frame'],self.templates) if self.templates else None
        if obs['state'] in ('WIN','GAME_OVER'):
            self.learning(obs,pieces);action=None if obs['state']=='WIN' else 0;data={};cert=None;reason=obs['state']
        elif not self.active and len(scene)<3:
            self.goal.observe(obs,self.last[0] if self.last else None);cert=self.goal.propose(obs)
            if cert:self.goal.commit(cert);action=cert['action']
            else:action=self.goal.choose(obs)
            data={};reason='established_goal_revision'
        else:
            if not self.active:self.goal.observe(obs,self.last[0] if self.last else None)
            self.active=True
            if self.level!=obs['levels_completed']:
                self.level=obs['levels_completed'];self.templates=copy.deepcopy(scene);pieces=locate(obs['frame'],self.templates);self.layout,self.layout_diagnostics=solve(scene);self.models={};self.trials.clear();self.selected=None;self.before_pieces=None;self.selection_sources=[];self.schedule=None
            self.learning(obs,pieces);legal=sorted(set(obs['available_actions'])&{1,2,3,4,5,7});action=None;data={};cert=None;reason='assembly_unresolved'
            if self.layout and pieces and all(pieces):
                if sum(self.trials.values())<15:action=min(legal,key=lambda a:(self.trials[a],a));reason='learn_selected_control'
                else:
                    if self.schedule is None:self.schedule=self.order(pieces,legal)
                    if self.schedule:
                        while self.schedule and pose(pieces[self.schedule[0]])==pose(self.layout[self.schedule[0]]):self.schedule.pop(0)
                    plans=[]
                    for i,g in self.layout.items():
                        if self.schedule and i!=self.schedule[0]:continue
                        if pose(pieces[i])==pose(g):continue
                        path=self.path(i,pieces,g,legal)
                        if path:plans.append((len(path)+(0 if i==self.selected else 2),i,path))
                    if plans:
                        _,i,path=min(plans)
                        if i!=self.selected:
                            cells=[p for p,c in absolute(pieces[i]).items() if c==1];cy=sum(y for y,x in cells)/len(cells);cx=sum(x for y,x in cells)/len(cells);y,x=min(cells,key=lambda p:(abs(p[0]-cy)+abs(p[1]-cx),p));action=6;data=dict(x=x,y=y);reason='select_piece'
                        else:
                            action=path[0][0];reason='assembly_plan';cert=dict(kind='marker_assembly_plan',action=action,data={},context=digest(obs),piece=i,pieces=pieces,goal_layout=self.layout,goal_is_hypothesis=True,path=[dict(action=a,predicted=o,rules=sorted(self.models[a]['rules']),support=self.models[a]['support']) for a,o in path],selection_evidence=self.selection_sources,retained_goal_feedback=copy.deepcopy(self.goal.goal_outcomes))
                    elif not complete(pieces):action=min(legal,key=lambda a:(self.trials[a],a));reason='control_or_path_repair'
            self.before_pieces=copy.deepcopy(pieces)
        if action is None and obs['state']=='NOT_FINISHED':
            tested=self.inquiries.setdefault(obs['levels_completed'],set());candidates=[]
            for obj in parts(obs['frame']):
                if obj['area']<9 or obj['y']<7 or obj['h']>40 or obj['w']>40:continue
                key=(obj['y'],obj['x'],obj['shape'])
                if key not in tested:candidates.append((obj,key))
            if self.inquiry_actions:
                action=self.inquiry_actions.pop(0);data={};reason='revealed_object_control_inquiry'
            elif candidates and 6 in obs['available_actions']:
                obj,k=min(candidates,key=lambda pair:(-pair[0]['area'],pair[1]));tested.add(k);cy=sum(y for y,x in obj['shape'])/obj['area'];cx=sum(x for y,x in obj['shape'])/obj['area'];y,x=min(obj['shape'],key=lambda p:(abs(p[0]-cy)+abs(p[1]-cx),p));action=6;data=dict(x=x+obj['x'],y=y+obj['y']);reason='unresolved_object_selection_inquiry';self.inquiry_actions=[a for a in (1,2,5) if a in obs['available_actions']]
            else:
                legal=sorted(set(obs['available_actions'])&{1,2,3,4,5,7})
                if legal:action=min(legal,key=lambda a:(self.trials[a],a));data={};reason='unresolved_control_inquiry'
        self.previous=raw;self.last=(action,data)
        if action in (1,2,3,4,5,7) and self.active:self.trials[action]+=1
        return dict(action=action,data=data,done=action is None,certificate=cert,advisor='marker_assembly_learner',diagnostics=dict(reason=reason,retained_transitions=len(self.history),selected=self.selected,assembly=self.layout_diagnostics,selection_events=len(self.selection_sources),planned_order=self.schedule,schedule_nodes=self.schedule_nodes,prediction_refutations=len(self.refutations),goal_outcomes=copy.deepcopy(self.goal.goal_outcomes)))
