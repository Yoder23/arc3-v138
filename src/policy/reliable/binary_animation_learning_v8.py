"""Learn multi-row column commands from legal animation observations."""
import copy
from collections import defaultdict,Counter
from binary_demonstration_probe_v3 import Agent as Inquiry, buttons
from binary_demonstration_bootstrap_v1 import components
from binary_demonstration_learning_v1 import bit_groups, heading, task


def columns(pairs):
    by_x=defaultdict(list)
    for a,b in pairs:by_x[a['box'][1]].append((a,b))
    result=[sorted(v,key=lambda p:p[0]['box'][0]) for x,v in sorted(by_x.items())]
    if len({len(v) for v in result})!=1:return []
    return result


def word(column,values):
    return tuple(values.index(a['ink'])+2*values.index(b['ink']) for a,b in column)


def actor_in(frame,pairs):
    top=min(a['box'][0] for a,b in pairs);lo=min(a['box'][1] for a,b in pairs)-8;hi=max(a['box'][1] for a,b in pairs)+8
    found=[o for o in components(frame) if lo<=o['box'][1]<=hi and o['box'][0]+o['box'][2]<top and
           3<=o['box'][2]==o['box'][3]<=24 and .75<=len(o['shape'])/o['box'][2]**2<1]
    return found[0] if len(found)==1 else None


def buttons(frame):
    obs=components(frame);marks=[o for o in obs if o['box'][2:] in ((1,3),(3,1))]
    if not marks:return []
    bottom=max(o['box'][0]+o['box'][2] for o in marks)
    return sorted([o for o in obs if o['box'][0]>=bottom and 5<=o['box'][2]==o['box'][3]<=9 and .4<len(o['shape'])/o['box'][2]**2<1 and all(p in o['shape'] for p in [(0,0),(0,o['box'][3]-1),(o['box'][2]-1,0),(o['box'][2]-1,o['box'][3]-1)])],key=lambda o:o['box'])


def goal_templates():
    base={(y,x)for y in range(5)for x in range(6)if x in(0,5)or y==4 or(y==3 and x in(2,3))}
    body={(y,x+1)for y in range(4)for x in range(4)if not(y==3 and x in(1,2))}
    h,w=5,6;hd=(1,0)
    for rotation in range(4):
        for scale in range(1,5):
            glyph=sorted((y*scale+dy,x*scale+dx)for y,x in base for dy in range(scale)for dx in range(scale))
            yy=min(y for y,x in body)*scale;xx=min(x for y,x in body)*scale
            yield (h*scale,w*scale),glyph,(yy,xx,4*scale,4*scale),hd
        base={(x,h-1-y)for y,x in base};body={(x,h-1-y)for y,x in body};h,w=w,h;hd=(hd[1],-hd[0])


def target_scene(frame,pairs):
    if not pairs:return None
    top=min(a['box'][0]for a,b in pairs);lo=max(0,min(a['box'][1]for a,b in pairs)-8);hi=min(64,max(a['box'][1]for a,b in pairs)+10)
    obs=components(frame);goals=[]
    for g in obs:
        if not(lo<=g['box'][1]<hi and g['box'][0]+g['box'][2]<top):continue
        for dims,glyph,body,hd in goal_templates():
            if g['box'][2:]==dims and sorted(g['shape'])==glyph:
                gy,gx=g['box'][:2];by,bx,bh,bw=body;goals.append((g,(gy+by,gx+bx,bh,bw),hd))
    repeated=Counter(o['ink']for o in obs if lo<=o['box'][1]<hi and o['box'][0]+o['box'][2]<top and 2<=o['box'][2]==o['box'][3]<=8 and len(o['shape'])==o['box'][2]**2)
    common={v for v,_ in repeated.most_common(2)}
    actors=[o for o in obs if lo<=o['box'][1]<=hi and o['box'][0]+o['box'][2]<top and 3<=o['box'][2]==o['box'][3]<=24 and .75<=len(o['shape'])/o['box'][2]**2<1 and o['ink']not in common and not any(g['box'][0]<=o['box'][0]<g['box'][0]+g['box'][2]and g['box'][1]<=o['box'][1]<g['box'][1]+g['box'][3]for g,_,_ in goals)]
    if len(actors)!=1 or len(goals)!=1:return None
    a=actors[0];g,b,hd=goals[0]
    return dict(actor=a,goal=g,target=tuple(b[:2]),target_body=dict(box=b),target_heading=hd,target_ink=g['ink'],floor_inks=sorted(common),template_is_goal_hypothesis=True)


def animation_evidence(raw,pairs,values,source,control_source):
    cs=columns(pairs);frames=raw.get('animation_frames',[])
    if not cs or len(frames)!=len(cs)+2:return []
    actors=[actor_in(f,pairs) for f in frames]
    if any(a is None for a in actors):return []
    if actors[-1]!=actors[-2]:return []
    result=[]
    for j,col in enumerate(cs):
        before,after=actors[j:j+2]
        delta=tuple(after['box'][k]-before['box'][k] for k in (0,1))
        result.append(dict(source=source,control_source=control_source,frame_indices=(j,j+1),column=j,word=word(col,values),pairs=col,before=before,after=after,delta=delta,heading_before=heading(before),heading_after=heading(after)))
    return result


def plan_program(scene,models,length,frame=None):
    a=scene['actor'];target=tuple(scene['target']);target_size=tuple(scene.get('target_body',a)['box'][2:]);start=tuple(a['box'])+(heading(a),a.get('ink'));states={start:()}
    grouped=defaultdict(list)
    for m in models.values():grouped[tuple(m['word'])].append(m)
    allowed=None
    goal_points={(scene['goal']['box'][0]+y,scene['goal']['box'][1]+x)for y,x in scene['goal']['shape']}if 'goal'in scene else set()
    if frame is not None:
        h,w=a['box'][2:];yy0=max(0,min(start[0],target[0])-h);yy1=min(64,max(start[0],target[0])+2*h);xx0=max(0,min(start[1],target[1])-w);xx1=min(64,max(start[1],target[1])+2*w)
        allowed=set(scene.get('floor_inks',[]))or{v for v,_ in Counter(frame[y][x] for y in range(yy0,yy1)for x in range(xx0,xx1)if frame[y][x]!=a['ink']).most_common(2)}
        allowed|={a['ink']}
    for depth in range(length):
        nxt={}
        for (y,x,h,w,d,ink),path in states.items():
            for key,samples in sorted(grouped.items()):
                exact=[m for m in samples if tuple(m['before']['box'][2:])==(h,w)]
                candidates=exact[-1:] or [m for m in samples if m['before']['box'][2:]==m['after']['box'][2:] and m['heading_before']==m['heading_after']]
                for model in candidates[-1:]:
                    dy,dx=model['delta'];ah,aw=tuple(model['after']['box'][2:])if exact else(h,w)
                    hd=d
                    before_hd,after_hd=model['heading_before'],model['heading_after']
                    if before_hd is not None and after_hd is not None and d is not None:
                        directions=[(-1,0),(0,1),(1,0),(0,-1)];turn=(directions.index(after_hd)-directions.index(before_hd))%4;hd=directions[(directions.index(d)+turn)%4]
                    color=model['after'].get('ink')if model['before'].get('ink')!=model['after'].get('ink')else ink
                    q=(y+dy,x+dx,ah,aw,hd,color)
                    if q in nxt or not(0<=q[0]<=64-ah and 0<=q[1]<=64-aw):continue
                    if allowed is not None:
                        size=max(abs(dy),abs(dx),1)
                        if any(frame[y+dy*t//size+iy][x+dx*t//size+ix]not in allowed and (y+dy*t//size+iy,x+dx*t//size+ix)not in goal_points for t in range(1,size+1)for iy in range(ah)for ix in range(aw)):continue
                    nxt[q]=path+(key,)
        states=nxt
    candidates=[p for q,p in states.items() if q[:2]==target and q[2:4]==target_size and (scene['target_heading']is None or q[4]==tuple(scene['target_heading']))and ('target_ink'not in scene or q[5]==scene['target_ink'])]
    return list(candidates[0])if candidates else None


class Agent(Inquiry):
    def __init__(self,prior=None):
        super().__init__(prior)
        self.learner_level=None;self.pending=None;self.level_data=None;self.models={};self.evidence=[]
        self.refutations=[];self.failures=[];self.successes=[];self.plan=None;self.model_archive=[]

    def respond(self,raw):
        if self.start_level is None or raw['levels_completed']==self.start_level:
            r=super().respond(raw)
            if self.bootstrap.rows:
                o=self.bootstrap.rows[0][0];self.main_background=raw['frame'][o['box'][0]-1][o['box'][1]+1]
            return r
        if raw['state']!='NOT_FINISHED':return dict(done=True,action=None,data={})
        if self.pending and self.pending['kind']=='submit':
            record=dict(source=self.t-1,level=self.pending['level'],plan=self.plan)
            if raw['levels_completed']>self.pending['level']:self.successes.append(record)
            else:self.failures.append(record)
            self.plan=None
        if self.learner_level!=raw['levels_completed']:
            if self.learner_level is not None:self.model_archive.append(dict(level=self.learner_level,models=list(copy.deepcopy(self.models).values()),evidence=copy.deepcopy(self.evidence)))
            self.learner_level=raw['levels_completed'];self.pending=None;self.models={};self.evidence=[];self.plan=None
            self.level_data=dict(source=self.t,controls=buttons(raw['frame']),control_index=0)
        values=self.bootstrap.values;groups=bit_groups(raw['frame'],values);pairs=groups.get(self.main_background,[])
        cs=columns(pairs);scene=target_scene(raw['frame'],pairs)
        if not cs or not scene:return dict(done=True,action=None,data={})
        if self.pending and self.pending['kind']=='demo':
            alternatives=[ps for bg,ps in groups.items() if bg!=self.main_background and columns(ps) and len(columns(ps)[0])==len(cs[0])]
            if len(alternatives)==1:
                evidence=animation_evidence(raw,alternatives[0],values,self.t,self.t-1)
                for m in evidence:
                    k=(tuple(m['word']),tuple(m['before']['box'][2:]),m['heading_before']);effect=(tuple(m['delta']),m['heading_after'],tuple(m['after']['box'][2:]))
                    if k in self.models and (tuple(self.models[k]['delta']),self.models[k]['heading_after'],tuple(self.models[k]['after']['box'][2:]))!=effect:
                        self.refutations.append(dict(old=self.models[k],new=m,reason='observed_command_effect_changed'))
                    self.models[k]=m;self.evidence.append(m)
        self.pending=None
        if self.level_data['control_index']<len(self.level_data['controls']):
            o=self.level_data['controls'][self.level_data['control_index']];self.level_data['control_index']+=1;y,x,h,w=o['box']
            data=dict(x=x+(w-1)//2,y=y+(h-1)//2);tag='retrieve_animation_demonstration';self.pending=dict(kind='demo')
        else:
            if self.plan is None:self.plan=plan_program(scene,self.models,len(cs),raw['frame'])
            if self.plan is None or any(q['level']==self.learner_level and q['plan']==self.plan for q in self.failures):return dict(done=True,action=None,data={})
            data=None;tag='write_observed_column_program'
            for desired,column in zip(self.plan,cs):
                for code,(a,b) in zip(desired,column):
                    for j,o in enumerate((a,b)):
                        if o['ink']!=values[(code>>j)&1]:
                            y,x,h,w=o['box'];data=dict(x=x+(w-1)//2,y=y+(h-1)//2);break
                    if data:break
                if data:break
            if data is None:
                line=max(a['box'][0] for a,b in pairs)
                controls=[o for o in components(raw['frame']) if 5<=min(o['box'][2:])<=max(o['box'][2:])<=12 and o['box'][0]>line+4 and len(o['shape'])>25]
                o=max(controls,key=lambda o:len(o['shape']));y,x,h,w=o['box'];data=dict(x=x+(w-1)//2,y=y+(h-1)//2);tag='test_observed_column_program';self.pending=dict(kind='submit',level=self.learner_level)
        self.queue=[];self.index=0;super().respond(raw)
        c=dict(kind='binary_animation_learning',source=self.t,tag=tag,anchor=None,anchor_source=None,memory=copy.deepcopy(self.memory),evidence=copy.deepcopy(self.evidence),models=list(copy.deepcopy(self.models).values()),values=values,scene=scene,plan=self.plan,refutations=copy.deepcopy(self.refutations),failures=copy.deepcopy(self.failures),successes=copy.deepcopy(self.successes),archive=copy.deepcopy(self.model_archive),model_generalization_is_hypothesis=True)
        self.previous=dict(raw=copy.deepcopy(raw),action=6,data=copy.deepcopy(data));self.t+=1
        return dict(done=False,action=6,data=data,certificate=c)
