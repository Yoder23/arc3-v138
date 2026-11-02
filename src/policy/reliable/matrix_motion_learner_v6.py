"""Learn editable input completion and visuomotor effects from public pixels.

Grid groups and matching-ink destinations are hypotheses, never game answers.
No IDs, fixed coordinates, game source, scorecards or supplied motion maps.
"""
from collections import Counter,defaultdict,deque
import copy
from centered_symbol_rows_v1 import tokens
from observed_edit_completion_v1 import EditLoop

def grids(frame):
    by_size=defaultdict(dict)
    for t in tokens(frame):
        if not t['hollow']:
            y,x,h,w=t['box'];by_size[h][y,x]=t
    out=[]
    for size,cells in by_size.items():
        for y,x in sorted(cells):
            for pitch in sorted({xx-x for yy,xx in cells if yy==y and xx-x>size}):
                for count in range(3,6):
                    points=[(y+i*pitch,x+j*pitch) for i in range(count) for j in range(count)]
                    if all(p in cells for p in points):
                        out.append(dict(box=(y,x,(count-1)*pitch+size,(count-1)*pitch+size),cells=[cells[p]['box'] for p in points],colors=[cells[p]['value'] for p in points]))
    return sorted(out,key=lambda g:(-len(g['cells'])*g['cells'][0][2]**2,g['box']))

def objects(frame,exclude=()):
    seen=set();out=[];height=len(frame);width=len(frame[0])
    for y in range(height):
        for x in range(width):
            if (y,x) in seen:continue
            color=frame[y][x];todo=[(y,x)];seen.add((y,x));cells=[]
            while todo:
                p=todo.pop();cells.append(p)
                for q in ((p[0]-1,p[1]),(p[0]+1,p[1]),(p[0],p[1]-1),(p[0],p[1]+1)):
                    if 0<=q[0]<height and 0<=q[1]<width and q not in seen and frame[q[0]][q[1]]==color:seen.add(q);todo.append(q)
            if not 1<=len(cells)<=24:continue
            yy=min(p[0] for p in cells);xx=min(p[1] for p in cells);h=max(p[0] for p in cells)-yy+1;w=max(p[1] for p in cells)-xx+1
            if max(h,w)>8 or any(gy<=yy<gy+gh and gx<=xx<gx+gw for gy,gx,gh,gw in exclude):continue
            out.append(dict(ink=color,box=(yy,xx,h,w),shape=tuple(sorted((a-yy,b-xx) for a,b in cells))))
    pairs=[]
    solid=[p for p in out if len(p['shape'])==p['box'][2]*p['box'][3]]
    for i,a in enumerate(solid):
        for b in solid[i+1:]:
            if a['ink']==b['ink'] or len(a['shape'])!=len(b['shape']):continue
            ay,ax,ah,aw=a['box'];by,bx,bh,bw=b['box']
            y=min(ay,by);x=min(ax,bx);h=max(ay+ah,by+bh)-y;w=max(ax+aw,bx+bw)-x
            if h!=w or not 2<=h<=8 or 2*len(a['shape'])!=h*w:continue
            pixels={(ay+dy,ax+dx) for dy,dx in a['shape']}|{(by+dy,bx+dx) for dy,dx in b['shape']}
            if len(pixels)!=h*w:continue
            pairs.append(dict(ink=tuple(sorted((a['ink'],b['ink']))),box=(y,x,h,w),shape=tuple((dy,dx) for dy in range(h) for dx in range(w)),parts=[a,b]))
    return [p for p in out if not any(p in q['parts'] for q in pairs)]+pairs

class Agent:
    def __init__(self,prior=None):
        self.prior=prior;self.active=False;self.level=None;self.t=0;self.previous=None;self.grid=None;self.edit=None;self.programs=[];self.program_index=0
        self.motions={};self.moving=None;self.goals=[];self.trials=Counter();self.blocked=set();self.experiences=[];self.episode_bank=[];self.passable=set();self.edit_started_at=0;self.input_motion_memory=[];self.contact=None
    def answer(self,raw,action,data,tag,extra=None):
        c=dict(kind='matrix_motion',tag=tag,observed_at=self.t,grid=copy.deepcopy(self.grid),motions=copy.deepcopy(self.motions),moving=copy.deepcopy(self.moving),goals=copy.deepcopy(self.goals),goal_is_hypothesis=True,program_index=self.program_index)
        if self.input_motion_memory:c['retained_input_skills']=copy.deepcopy(self.input_motion_memory)
        if extra:c.update(extra)
        self.previous=dict(raw=copy.deepcopy(raw),action=action,data=copy.deepcopy(data),certificate=copy.deepcopy(c),source=self.t)
        self.t+=1;self.trials[action]+=1;return dict(done=False,action=action,data=data,certificate=c)
    def observe(self,raw):
        old=self.previous
        if not old or old['raw']['state']!=raw['state'] or old['raw']['levels_completed']!=raw['levels_completed']:return
        exclude=[self.grid['box']] if self.grid else []
        before=objects(old['raw']['frame'],exclude);after=objects(raw['frame'],exclude)
        if old['action']==6:return
        matches=[]
        for b in before:
            if any(q==b for q in after):continue
            candidates=[q for q in after if q['ink']==b['ink'] and q['shape']==b['shape'] and 0<abs(q['box'][0]-b['box'][0])+abs(q['box'][1]-b['box'][1])<=8]
            if len(candidates)!=1:continue
            q=candidates[0];delta=(q['box'][0]-b['box'][0],q['box'][1]-b['box'][1])
            if (delta[0]==0)==(delta[1]==0):continue
            goals=[g for g in after if ((g['ink'] in q['ink'] and not g.get('parts') and len(g['shape'])==g['box'][2]*g['box'][3]) if q.get('parts') else g['ink']==q['ink']) and g!=q and g in before]
            if goals:matches.append((len(q['shape']),q,b,delta,goals))
        if matches:
            _,q,b,delta,goals=min(matches,key=lambda x:(not bool(x[1].get('parts')),x[0],str(x[1]['ink']),x[1]['box']))
            self.moving=q;self.goals=[dict(g,observed_at=self.t) for g in goals];self.motions[old['action']]=dict(delta=delta,support=old['source'],before=b,after=q)
            for dy,dx in q['shape']:
                y,x=q['box'][0]+dy,q['box'][1]+dx;self.passable.add(old['raw']['frame'][y][x])
            self.experiences.append(dict(source=old['source'],action=old['action'],delta=delta,program=self.program_index,kind='observed_motion'))
        elif self.moving:
            same=[q for q in after if q['ink']==self.moving['ink'] and q['shape']==self.moving['shape'] and q['box']==self.moving['box']]
            if same:
                self.moving=same[0]
                self.blocked.add((tuple(self.moving['box'][:2]),old['action'],self.program_index));self.experiences.append(dict(source=old['source'],action=old['action'],program=self.program_index,kind='no_observed_motion'))
            else:
                m=self.motions.get(old['action']);body=self.moving
                if m:
                    dest=tuple(body['box'][i]+m['delta'][i] for i in (0,1))
                    hit=[g for g in self.goals if g['box'][0]-1<=dest[0]<=g['box'][0]+g['box'][2] and g['box'][1]-1<=dest[1]<=g['box'][1]+g['box'][3]]
                    if hit:self.contact=dict(source=old['source'],action=old['action'],body=copy.deepcopy(body),goal=copy.deepcopy(hit[0]),motion=copy.deepcopy(m),attempt=0,limit=max(hit[0]['box'][2:])+1,hypothesis='predicted_goal_adjacency_with_visually_merged_body')
                self.moving=None
    def respond(self,raw):
        assert set(raw)=={'frame','state','available_actions','levels_completed'}
        if raw['state']=='WIN':return dict(done=True,action=None,data={})
        if self.level!=raw['levels_completed']:
            self.contact=None
            if self.previous and self.grid and raw['levels_completed']>self.level:
                values={self.previous['raw']['frame'][y][x] for y,x,h,w in self.grid['cells']}
                if len(values)==1:self.input_motion_memory.append(dict(level=self.level,observed_progress_at=self.t-1,uniform_ink=next(iter(values)),grid=copy.deepcopy(self.grid)))
            if self.level is not None:self.episode_bank.append(dict(level=self.level,motions=copy.deepcopy(self.motions),experiences=copy.deepcopy(self.experiences),program=self.program_index))
            self.level=raw['levels_completed'];self.previous=None;self.grid=None;self.edit=None;self.motions={};self.moving=None;self.goals=[];self.trials=Counter();self.blocked=set();self.passable=set();self.program_index=0
        if raw['state']=='GAME_OVER':return self.answer(raw,0,{},'reset_after_failure')
        if self.grid is None:
            found=grids(raw['frame'])
            if not found or 6 not in raw['available_actions']:return self.prior.respond(raw) if self.prior and not self.active else dict(done=True,action=None,data={})
            self.grid=dict(found[0],observed_at=self.t);groups=defaultdict(list)
            for box,color in zip(self.grid['cells'],self.grid['colors']):
                y,x,h,w=box;groups[color].append((x+(w-1)//2,y+(h-1)//2))
            preferred=self.input_motion_memory[-1]['uniform_ink'] if self.input_motion_memory else None
            self.programs=[ps for ink,ps in sorted(groups.items(),key=lambda item:(item[0]==preferred,len(item[1]),item[1]))];self.edit=EditLoop(self.programs[0]);self.edit_started_at=self.t;self.active=True
        self.observe(raw)
        if self.contact:
            if self.contact['attempt']<self.contact['limit']:
                self.contact['attempt']+=1
                return self.answer(raw,self.contact['action'],{},'test_goal_contact',dict(goal_contact=copy.deepcopy(self.contact)))
            self.experiences.append(dict(kind='unconfirmed_goal_contact',evidence=copy.deepcopy(self.contact)));self.contact=None
        if self.edit:
            proposal=self.edit.propose(raw)
            if proposal:return self.answer(raw,proposal['action'],proposal['data'],'verify_input_edit',dict(edit=proposal['certificate'],edit_start=self.edit_started_at))
            complete=self.edit.completed(raw);self.experiences.append(dict(source=self.t,kind='input_configuration_completed',completed=complete,program=self.program_index,evidence=copy.deepcopy(self.edit.evidence)))
            self.edit=None;self.moving=None;self.motions={};self.blocked=set();self.passable=set()
            if not complete:return dict(done=True,action=None,data={})
        allowed=[a for a in raw['available_actions'] if a not in (0,6,7)]
        if not allowed:return dict(done=True,action=None,data={})
        if self.moving and self.goals:
            at=tuple(self.moving['box'][:2]);goals=[tuple(g['box'][:2]) for g in self.goals]
            distance=lambda p:min(abs(p[0]-g[0])+abs(p[1]-g[1]) for g in goals)
            choices=[]
            for a,m in self.motions.items():
                dest=tuple(at[i]+m['delta'][i] for i in (0,1))
                if (at,a,self.program_index) not in self.blocked and distance(dest)<distance(at):choices.append((distance(dest),a))
            if choices:return self.answer(raw,min(choices)[1],{},'move_toward_visual_goal')
            unknown=[a for a in allowed if a not in self.motions and (at,a,self.program_index) not in self.blocked]
            if unknown:return self.answer(raw,min(unknown,key=lambda a:(self.trials[a],a)),{},'conditional_motion_inquiry')
        else:
            unknown=[a for a in allowed if self.trials[a]<3]
            if unknown:return self.answer(raw,min(unknown,key=lambda a:(self.trials[a],a)),{},'motion_inquiry')
        self.program_index+=1
        if self.program_index<len(self.programs):
            self.edit=EditLoop(self.programs[self.program_index]);self.edit_started_at=self.t
            proposal=self.edit.propose(raw)
            if proposal:return self.answer(raw,proposal['action'],proposal['data'],'verify_input_edit',dict(edit=proposal['certificate'],edit_start=self.edit_started_at))
        return dict(done=True,action=None,data={})
