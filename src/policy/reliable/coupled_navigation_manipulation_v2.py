"""Learn selection-dependent obstacle motion and test parking outside a goal route."""
import copy
from collections import deque
from coupled_navigation_core_v10 import Agent as Prior,actors,cells,landmarks,board,predict
from structured_interaction_probe_v1 import parts
from visual_transform_learner import digest

def recolor_mode(agent,obs):
    if not (agent.last==6 and agent.previous_pos and agent.signature and agent.previous and agent.previous['levels_completed']==obs['levels_completed'] and obs['state']=='NOT_FINISHED'):return None
    color,size=agent.signature;foot=cells(agent.previous_pos,size);colors={obs['frame'][y][x] for y,x in foot}
    if len(colors)!=1 or color in colors:return None
    inactive=next(iter(colors));_,pos=actors(obs['frame'],(inactive,size))
    if not pos or set(pos)!=set(agent.previous_pos):return None
    changes=[(y,x,a,b) for y,(old,new) in enumerate(zip(agent.previous['frame'][1:63],obs['frame'][1:63]),1) for x,(a,b) in enumerate(zip(old,new)) if a!=b and (y,x) not in foot]
    if not changes or len({(a,b) for y,x,a,b in changes})!=1:return None
    old,new=changes[0][2:];pixels={(y,x) for y,x,a,b in changes};y=min(q[0] for q in pixels);x=min(q[1] for q in pixels);shape=tuple(sorted((a-y,b-x) for a,b in pixels))
    if len(shape)>((size+1)//2)**2:return None
    return dict(source=digest(dict(before=agent.previous,action=agent.last,data=agent.last_data,after=obs)),level=agent.level,signature=agent.signature,inactive=inactive,marker_color=old,selected_color=new,shape=shape,origin=(y,x),actor_positions=agent.previous_pos,observations=[],models={},failures=set(),attempts=0,initial_origin=(y,x))

class Agent(Prior):
    def __init__(self):
        super().__init__();self.manipulation=None;self.manipulation_memories=[]
    def selected(self,obs,m):
        points={(y,x) for y,row in enumerate(obs['frame'][1:63],1) for x,v in enumerate(row) if v==m['selected_color']}
        if len(points)!=len(m['shape']):return None
        y=min(q[0] for q in points);x=min(q[1] for q in points)
        return (y,x) if tuple(sorted((a-y,b-x) for a,b in points))==m['shape'] else None
    def relocate(self,obs,m,origin):
        if not self.floor_counts:return None,dict(reason='floor_unknown')
        floor=self.floor_counts.most_common(1)[0][0];size=self.signature[1];effects,_=self.controls();f=board(obs,m['actor_positions'],size,floor)
        for q in landmarks(obs,floor,size,self.hazards,m['inactive']):
            for y,x in q['pixels']:f[y][x]=floor
        for dy,dx in m['shape']:f[origin[0]+dy][origin[1]+dx]=floor
        # Build a relaxed actor route; all small-object passages are explicitly hypotheses.
        queue=deque([(m['actor_positions'],[])]);seen={m['actor_positions']};route=None
        while queue and len(seen)<25000:
            here,path=queue.popleft()
            if here[0]==here[1] and path:route=path;break
            for a,delta in sorted(effects.items()):
                after=predict(f,here,size,delta,floor,self.hazards)
                if after is not None and after not in seen:seen.add(after);queue.append((after,path+[after]))
        if route is None:return None,dict(reason='relaxed_goal_unreachable',expanded=len(seen))
        corridor=set().union(*(cells(p,size) for p in [m['actor_positions']]+route))
        occupied={(origin[0]+dy,origin[1]+dx) for dy,dx in m['shape']}
        if not occupied&corridor and origin!=m['initial_origin']:return ('release',None),dict(reason='relocated_outside_goal_route',expanded=len(seen))
        proposals={a:tuple(delta[0]) for a,delta in effects.items() if a in (1,2,3,4,7)}
        for a,deltas in m['models'].items():
            if len(deltas)==1:proposals[a]=next(iter(deltas))
        q=deque([(origin,[])]);visited={origin};frame=obs['frame'];best=None
        while q and len(visited)<2000:
            here,path=q.popleft();foot={(here[0]+dy,here[1]+dx) for dy,dx in m['shape']}
            if path and not foot&corridor:best=path;break
            for a,(dy,dx) in sorted(proposals.items()):
                if (here,a) in m['failures']:continue
                nxt=(here[0]+dy,here[1]+dx);pts={(nxt[0]+oy,nxt[1]+ox) for oy,ox in m['shape']}
                if nxt in visited or not all(0<y<63 and 0<x<63 and ((y,x) in occupied or frame[y][x]==floor) for y,x in pts):continue
                visited.add(nxt);q.append((nxt,path+[(a,nxt)]))
        if best:return ('move',best[0]),dict(reason='test_obstacle_relocation_hypothesis',expanded=len(seen),object_expanded=len(visited),predicted=best[0][1],control_transfer_is_hypothesis=True)
        # No complete parking route yet: collect an untried conditional-control observation.
        for a in sorted(set(obs['available_actions'])&{1,2,3,4,7}):
            if (origin,a) not in m['failures'] and a not in m['models']:return ('probe',(a,None)),dict(reason='identify_selected_object_controls',expanded=len(seen))
        return ('release',None),dict(reason='no_supported_parking_route',expanded=len(seen),object_expanded=len(visited))
    def respond(self,obs):
        if self.manipulation is None:self.manipulation=recolor_mode(self,obs)
        m=self.manipulation;origin=self.selected(obs,m) if m else None
        if m and self.previous and self.last in (1,2,3,4,7) and origin:
            before=m['origin'];delta=(origin[0]-before[0],origin[1]-before[1]);source=digest(dict(before=self.previous,action=self.last,data=self.last_data,after=obs));m['observations'].append(dict(source=source,action=self.last,before=before,after=origin,delta=delta))
            if delta==(0,0):m['failures'].add((before,self.last))
            else:m['models'].setdefault(self.last,{}).setdefault(delta,[]).append(source)
            m['origin']=origin
        if m:
            _,restored=actors(obs['frame'],m['signature'])
            if restored or obs['state']!='NOT_FINISHED' or obs['levels_completed']!=m['level'] or origin is None:
                self.manipulation_memories.append(dict(**m,outcome=digest(obs),restored=bool(restored),progress=obs['levels_completed']>m['level']));self.manipulation=None;m=None
        response=super().respond(obs)
        if m:
            choice,diagnostic=self.relocate(obs,m,origin);m['attempts']+=1
            if choice is None or m['attempts']>48:choice=('release',None)
            if choice[0]=='release':
                y,x=m['actor_positions'][0];action=6;data=dict(x=x+self.signature[1]//2,y=y+self.signature[1]//2)
            else:action=choice[1][0];data={}
            self.last=action;self.last_data=copy.deepcopy(data);self.predicted=None;response.update(action=action,data=data,done=False,certificate=None);response['diagnostics'].update(diagnostic);response['diagnostics']['selection_source']=m['source']
        response['diagnostics'].update(manipulation_active=bool(m),manipulation_memories=len(self.manipulation_memories))
        return response
