"""After ordinary landmark plans fail, test a retained program from aligned visible vantage points."""
from collections import Counter
import copy
from matrix_program_bank_v2 import Agent as Base
from observed_program_completion_v1 import ProgramEditLoop
from matrix_reference_programs_v1 import programs
from matrix_reference_cues_v2 import cues
from matrix_intermediate_learner_v3 import reachable,path,inside
from matrix_motion_learner_v6 import objects
from observed_edit_completion_v1 import EditLoop

class Agent(Base):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.ranged=None;self.ranged_attempts=set();self.ranged_steps=0;self.ranged_memory=[];self.disable_ranged=False;self.heading_witness=None;self.orientations={}
    def answer(self,raw,action,data,tag,extra=None):
        return super().answer(raw,action,data,tag,dict(ranged_memory=copy.deepcopy(self.ranged_memory),observed_input_effects=copy.deepcopy(self.observed_input_effects),orientations=copy.deepcopy(self.orientations),heading_witness=copy.deepcopy(self.heading_witness),reference_cues=[dict(c,observed_at=self.t) for c in cues(raw,self.grid)],**(extra or {})))
    def emit(self,raw,a,d,phase,route=None,extra=None):
        self.ranged_steps+=1
        p=dict(phase=phase,landmark=copy.deepcopy(self.ranged['landmark']),pose=self.ranged['pose'],direction=self.ranged['direction'],route=route or [],hypothesis='position_and_orientation_condition_the_observed_input_skill')
        return self.answer(raw,a,d,'ranged_'+phase,dict(ranged_plan=p,**(extra or {})))
    def observe(self,raw):
        old=self.previous
        super().observe(raw)
        if not old or old['action'] in (0,6,7) or old['raw']['levels_completed']!=raw['levels_completed'] or not self.moving or not self.moving.get('parts'):return
        body=self.moving;y,x,h,w=body['box']
        def vector(part):
            yy,xx,hh,ww=part['box'];return (2*yy+hh-2*y-h,2*xx+ww-2*x-w)
        if self.heading_witness is None and old['action'] in self.motions:
            m=self.motions[old['action']]
            if m['support']==old['source']:
                part=max(body['parts'],key=lambda p:sum(a*b for a,b in zip(vector(p),m['delta'])))
                self.heading_witness=dict(source=old['source'],ink=part['ink'],before=m['before'],after=m['after'],delta=m['delta'])
        if self.heading_witness:
            parts=[p for p in body['parts'] if p['ink']==self.heading_witness['ink']]
            if len(parts)==1:
                v=vector(parts[0]);direction=tuple((q>0)-(q<0) for q in v)
                if abs(direction[0])+abs(direction[1])==1:self.orientations[old['action']]=dict(source=old['source'],direction=direction,body=copy.deepcopy(body))
    def respond(self,raw):
        if self.level!=raw['levels_completed'] or self.previous and self.previous['action']==0:self.heading_witness=None;self.orientations={}

        if self.level!=raw['levels_completed'] or raw['state']!='NOT_FINISHED':self.ranged=None;self.ranged_steps=0
        if self.ranged is None:
            response=super().respond(raw)
            if not response['done'] or self.disable_ranged or raw['state']!='NOT_FINISHED' or not self.moving or not self.motions or self.ranged_steps>=120:return response
        else:self.observe(raw)
        if not self.moving or self.ranged_steps>=120:return dict(done=True,action=None,data={})
        parents,bg=reachable(self,raw);h,w=self.moving['box'][2:];at=tuple(self.moving['box'][:2])
        if self.ranged is None:
            reference_inks={c['ink'] for c in cues(raw,self.grid)};choices=[];palette=set(self.moving['ink']) if self.moving.get('parts') else {self.moving['ink']}
            for landmark in objects(raw['frame'],[self.grid['box']]+[p['panel'] for p in programs(raw['frame'],self.grid)]):
                if landmark.get('parts') or landmark['ink'] in getattr(self,'ranged_excluded_inks',set()) or landmark['ink'] in palette|{bg} or landmark['ink'] in self.passable:continue
                y,x,hh,ww=landmark['box'];cy=y+(hh-1)/2;cx=x+(ww-1)/2
                for q in parents:
                    by=q[0]+(h-1)/2;bx=q[1]+(w-1)/2
                    if abs(by-cy)<1:direction=(0,1 if cx>bx else -1);distance=abs(cx-bx)
                    elif abs(bx-cx)<1:direction=(1 if cy>by else -1,0);distance=abs(cy-by)
                    else:continue
                    if not 2<=distance<=24:continue
                    controls=[a for a,m in self.orientations.items() if tuple(m['direction'])==direction]
                    if not controls:continue
                    key=self.level,tuple(landmark['box']),landmark['ink'],q,direction
                    if key in self.ranged_attempts:continue
                    route=path(parents,q);tried=sum(1 for level,box,ink,pose,heading in self.ranged_attempts if level==self.level and box==tuple(landmark['box']) and ink==landmark['ink']);choices.append((landmark['ink'] not in reference_inks,tried,len(route),q,landmark,direction,key,controls[0]))
            if not choices:return dict(done=True,action=None,data={})
            _,_,_,pose,lm,direction,key,control=min(choices,key=lambda x:(x[0],x[1],x[2],x[3],x[4]['box']));self.ranged_attempts.add(key)
            self.ranged=dict(landmark=dict(lm,observed_at=self.t),pose=pose,direction=direction,control=control,phase='approach',start=self.t,clear_no_effects=Counter(),clear_steps=0,edit=None)
        e=self.ranged
        if e['phase']=='approach':
            if e['pose'] not in parents:return self.finish(raw,'approach_refuted')
            route=path(parents,e['pose'])
            if route:return self.emit(raw,route[0],{},'approach',route)
            e['phase']='clear';return self.emit(raw,e['control'],{},'orient')
        if e['phase']=='clear':
            if self.previous and self.previous['certificate'].get('ranged_plan',{}).get('phase')=='clear':
                old=self.previous;x,y=old['data']['x'],old['data']['y']
                if old['raw']['frame'][y][x]==raw['frame'][y][x]:e['clear_no_effects'][x,y]+=1
            selected=[]
            if self.selection_record:
                for y,x,hh,ww in self.grid['cells']:
                    point=x+(ww-1)//2,y+(hh-1)//2
                    if raw['frame'][y][x]==self.selection_record['ink'] and e['clear_no_effects'][point]<2:selected.append(point)
            if selected and e['clear_steps']<2*len(self.grid['cells']):
                e['clear_steps']+=1;x,y=selected[0];return self.emit(raw,6,dict(x=x,y=y),'clear')
            e['phase']='program';e['edit']=ProgramEditLoop(self.programs[0],self.grid,self.t) if self.program_bindings else EditLoop(self.programs[0]);e['edit_start']=self.t
            if self.program_bindings:self.program_editors.append(e['edit'])
        if e['phase']=='program':
            proposal=e['edit'].propose(raw)
            if proposal:return self.emit(raw,proposal['action'],proposal['data'],'program',extra=dict(edit=proposal['certificate'],edit_start=e['edit_start']))
            return self.finish(raw,'input_completed' if e['edit'].completed(raw) else 'input_unconfirmed')
        return dict(done=True,action=None,data={})
    def finish(self,raw,outcome):
        e=self.ranged;self.ranged_memory.append(dict(start=e['start'],end=self.t,landmark=e['landmark'],pose=e['pose'],direction=e['direction'],outcome=outcome,world_effect_unconfirmed=True));self.ranged=None
        # One actual inquiry separates experiments, without observing twice.
        a=min(self.motions,key=lambda a:(self.trials[a],a))
        return self.answer(raw,a,{},'ranged_alternative_probe')
