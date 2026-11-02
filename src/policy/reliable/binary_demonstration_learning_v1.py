"""Infer command hypotheses from visible examples and test exact-length programs."""
import copy
import itertools
from collections import Counter
from binary_demonstration_probe_v3 import Agent as Inquiry, buttons
from binary_demonstration_bootstrap_v1 import components

DIRS = ((-1,0),(0,1),(1,0),(0,-1))


def bit_groups(frame, values):
    obs=components(frame)
    hs=[o for o in obs if o['box'][2:]==(1,3)]
    vs=[o for o in obs if o['box'][2:]==(3,1)]
    groups={}
    for h in hs:
        for v in vs:
            y,x,_,_=h['box']
            if v['box'][:2]!=(y+2,x+1) or h['ink'] not in values or v['ink'] not in values:continue
            bg=frame[y-1][x+1]
            groups.setdefault(bg,[]).append((h,v))
    for bg in groups:groups[bg].sort(key=lambda p:p[0]['box'])
    return groups


def heading(o):
    h,w=o['box'][2:]
    missing={(y,x) for y in range(h) for x in range(w)}-set(map(tuple,o['shape']))
    if not missing:return None
    dy=sum(2*y-h+1 for y,x in missing);dx=sum(2*x-w+1 for y,x in missing)
    if dy and not dx:return ((dy>0)-(dy<0),0)
    if dx and not dy:return (0,(dx>0)-(dx<0))
    return None


def codes(pairs,values):
    return [values.index(a['ink'])+2*values.index(b['ink']) for a,b in pairs]


def task(frame,pairs):
    if not pairs:return None
    top=min(a['box'][0] for a,b in pairs)
    lo=min(a['box'][1] for a,b in pairs)-8;hi=max(a['box'][1] for a,b in pairs)+10
    obs=components(frame)
    actors=[o for o in obs if lo<=o['box'][1]<=hi and o['box'][0]+o['box'][2]<top and
            3<=o['box'][2]==o['box'][3]<=6 and .75<=len(o['shape'])/o['box'][2]**2<1]
    results=[]
    for a in actors:
        for g in obs:
            if g['ink']==a['ink'] and a['box'][2]<min(g['box'][2:]) and max(g['box'][2:])<=a['box'][2]+2 and len(g['shape'])<.7*g['box'][2]*g['box'][3]:
                target=tuple(g['box'][j]+(g['box'][j+2]-a['box'][j+2]+1)//2 for j in (0,1))
                results.append(dict(actor=a,goal=g,target=target))
    return results[0] if len(results)==1 else None


def infer_models(demos,known):
    results=[]
    for model in itertools.permutations(DIRS):
        if any(model[k]!=tuple(v) for k,v in known.items()):continue
        if any(d['heading'] is not None and model[d['codes'][-1]]!=tuple(d['heading']) for d in demos):continue
        if len(demos)<2:continue
        compatible=[]
        for stride in range(1,9):
            origins=[]
            for d in demos:
                delta=[sum(model[c][j] for c in d['codes'])*stride for j in (0,1)]
                origins.append(tuple(d['actor']['box'][j]-delta[j] for j in (0,1)))
            if len(set(origins))==1:compatible.append(stride)
        if compatible:results.append(dict(directions=model,display_strides=compatible))
    return results


def compose(frame,scene,model,length,stride):
    a=scene['actor'];start=tuple(a['box'][:2]);target=tuple(scene['target']);h,w=a['box'][2:]
    # Search through the visible floor; crossing a foreign pixel is tentative
    # blocking, not a claim that its hidden collision semantics are known.
    y0=max(0,min(start[0],target[0])-h);y1=min(64,max(start[0],target[0])+2*h)
    x0=max(0,min(start[1],target[1])-w);x1=min(64,max(start[1],target[1])+2*w)
    floor=[v for v,_ in Counter(frame[y][x] for y in range(y0,y1) for x in range(x0,x1) if frame[y][x]!=a['ink']).most_common(2)]
    allowed=set(floor+[a['ink']]);states={start:()}
    for depth in range(length):
        nxt={}
        for at,path in states.items():
            for code,(dy,dx) in enumerate(model):
                q=at[0]+dy*stride,at[1]+dx*stride
                if q in nxt or not(0<=q[0]<=64-h and 0<=q[1]<=64-w):continue
                if sum(abs(q[j]-target[j]) for j in (0,1))>(length-depth-1)*stride:continue
                clear=True
                for t in range(1,stride+1):
                    yy,xx=at[0]+dy*t,at[1]+dx*t
                    if any(frame[y][x] not in allowed for y in range(yy,yy+h) for x in range(xx,xx+w)):clear=False;break
                if clear:nxt[q]=path+(code,)
        states=nxt
    return list(states[target]) if target in states else None


class Agent(Inquiry):
    def __init__(self,prior=None):
        super().__init__(prior)
        self.level_data=None;self.demonstrations=[];self.known={};self.successes=[];self.rejections=[]
        self.pending=None;self.plan=None;self.failed=set();self.learner_level=None;self.known_sources=[]

    def respond(self,raw):
        # Reuse the audited observation ledger and bootstrap, but override the
        # inquiry queue with learner-generated actions after the first progress.
        if self.start_level is None or raw['levels_completed']==self.start_level:
            response=super().respond(raw)
            if not response['done']:
                self.first_scene=task(raw['frame'],list(zip(*self.bootstrap.rows))) if self.bootstrap.rows else None
                self.main_background=raw['frame'][self.bootstrap.rows[0][0]['box'][0]-1][self.bootstrap.rows[0][0]['box'][1]+1] if self.bootstrap.rows else None
            return response
        previous=self.previous
        if self.pending and self.pending['kind']=='submit':
            if raw['levels_completed']>self.pending['level']:
                self.successes.append(dict(source=self.t-1,plan=self.pending['plan'],directions=self.pending['model'],level=self.pending['level']))
            else:
                self.rejections.append(dict(source=self.t-1,plan=self.pending['plan'],directions=self.pending['model'],level=self.pending['level'],reason='submitted_predicted_goal_without_progress'))
                self.failed.add(tuple(map(tuple,self.pending['model'])));self.plan=None
        if self.learner_level!=raw['levels_completed']:
            if self.learner_level is None and self.first_scene:
                direction=tuple((self.first_scene['target'][j]>self.first_scene['actor']['box'][j])-(self.first_scene['target'][j]<self.first_scene['actor']['box'][j]) for j in (0,1))
                if direction in DIRS:
                    self.known[self.bootstrap.test]=direction
                    self.known_sources.append(dict(source=self.t-1,code=self.bootstrap.test,direction=direction,scene=self.first_scene))
            self.learner_level=raw['levels_completed'];self.demonstrations=[];self.plan=None;self.failed=set();self.pending=None
            self.level_data=dict(source=self.t,controls=buttons(raw['frame']),control_index=0)
        values=self.bootstrap.values
        groups=bit_groups(raw['frame'],values)
        pairs=groups.get(self.main_background,[])
        scene=task(raw['frame'],pairs)
        if self.pending and self.pending['kind']=='demo':
            alternatives=[ps for bg,ps in groups.items() if bg!=self.main_background and len(ps)==len(pairs)]
            if len(alternatives)==1:
                ps=alternatives[0];top=min(a['box'][0] for a,b in ps);lo=min(a['box'][1] for a,b in ps)-8;hi=max(a['box'][1] for a,b in ps)+8
                actors=[o for o in components(raw['frame']) if lo<=o['box'][1]<=hi and o['box'][0]+o['box'][2]<top and 3<=o['box'][2]==o['box'][3]<=6 and .75<=len(o['shape'])/o['box'][2]**2<1]
                if len(actors)==1:
                    self.demonstrations.append(dict(source=self.t,control_source=self.t-1,control=self.pending['data'],pairs=ps,codes=codes(ps,values),actor=actors[0],heading=heading(actors[0])))
        self.pending=None
        if not scene or not pairs:return dict(done=True,action=None,data={})
        if self.level_data['control_index']<len(self.level_data['controls']):
            anchor=self.level_data['controls'][self.level_data['control_index']];self.level_data['control_index']+=1
            y,x,h,w=anchor['box'];data=dict(x=x+(w-1)//2,y=y+(h-1)//2);tag='retrieve_command_demonstration';self.pending=dict(kind='demo',data=data)
        else:
            models=infer_models(self.demonstrations,self.known)
            if self.plan is None:
                for m in models:
                    if tuple(m['directions']) in self.failed:continue
                    plan=compose(raw['frame'],scene,m['directions'],len(pairs),scene['actor']['box'][2])
                    if plan is not None:self.plan=plan;self.selected_model=m;break
            if self.plan is None:return dict(done=True,action=None,data={})
            data=None;tag='write_inferred_program'
            for code,(a,b) in zip(self.plan,pairs):
                for j,o in enumerate((a,b)):
                    if o['ink']!=values[(code>>j)&1]:
                        y,x,h,w=o['box'];data=dict(x=x+(w-1)//2,y=y+(h-1)//2);break
                if data:break
            if data is None:
                line=max(a['box'][0]for a,b in pairs)
                candidates=[o for o in components(raw['frame']) if 5<=min(o['box'][2:])<=max(o['box'][2:])<=12 and o['box'][0]>line+4 and len(o['shape'])>25]
                anchor=max(candidates,key=lambda o:len(o['shape']));y,x,h,w=anchor['box'];data=dict(x=x+(w-1)//2,y=y+(h-1)//2);tag='test_inferred_program'
                self.pending=dict(kind='submit',plan=self.plan,model=self.selected_model['directions'],level=raw['levels_completed'])
        # Let the ledger consume the preceding real outcome. Empty queue stops
        # the fixed probe before it chooses any action or records a fake one.
        self.queue=[];self.index=0
        super().respond(raw)
        response=dict(done=False,action=6,data=data)
        response['certificate']=dict(kind='binary_demonstration_learning',source=self.t,tag=tag,anchor=None,anchor_source=None,memory=copy.deepcopy(self.memory),demonstrations=copy.deepcopy(self.demonstrations),known=copy.deepcopy(self.known),known_sources=copy.deepcopy(self.known_sources),values=values,successes=copy.deepcopy(self.successes),rejections=copy.deepcopy(self.rejections),models=infer_models(self.demonstrations,self.known),plan=self.plan,scene=scene,model_family_is_hypothesis=True)
        self.previous=dict(raw=copy.deepcopy(raw),action=6,data=copy.deepcopy(data));self.t+=1
        return response
