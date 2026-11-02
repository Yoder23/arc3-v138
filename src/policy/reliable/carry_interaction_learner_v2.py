"""Learn motion and attachment from legal observations; retain tentative visible goals."""
from collections import Counter,deque
import copy
from carry_affordance_geometry_v2 import scene

def plus(a,b):return tuple(x+y for x,y in zip(a,b))
def minus(a,b):return tuple(x-y for x,y in zip(a,b))

class Controller:
    def __init__(self,prior=None,retain=True):
        self.prior=prior;self.retain=retain;self.active=False;self.t=0;self.previous=None
        self.signature=None;self.phase=None;self.goal=None;self.motions={};self.blocked=set();self.held=None
        self.attachment=None;self.mode=None;self.target=None;self.trials=Counter();self.history=[];self.no_goal_steps=0

    def view(self,raw):
        s=scene(raw['frame'])
        if self.signature is None and s['cargo'] and s['bodies']:
            c=s['cargo'][0];n=c['box'][2]
            bodies=[b for b in s['bodies'] if b['box'][2:]==(n,n)]
            if len(bodies)==1:
                b=bodies[0];self.signature=(n,c['inner_ink'],b['fill_ink'],b['stripe_ink']);self.phase=(b['box'][0]%n,b['box'][1]%n)
        if self.signature is None:return None
        n,ink,fill,stripe=self.signature
        bodies=[b for b in s['bodies'] if b['box'][2:]==(n,n) and b['fill_ink']==fill and b['stripe_ink']==stripe]
        bodies=[b for b in bodies if (b['box'][0]%n,b['box'][1]%n)==self.phase]
        if len(bodies)!=1:return None
        cargo=[v for v in s['framed'] if v['box'][2:]==(n,n) and v['inner_ink']==ink]
        containers=[v for v in s['containers'] if (v['box'][2]==n or v['box'][3]==n) and v['box'][2]*v['box'][3]==len(cargo)*n*n]
        return dict(body=bodies[0],cargo=cargo,containers=containers,n=n)

    def positions(self,v):return {tuple(c['box'][:2]) for c in v['cargo']}

    def record(self,raw,v):
        old=self.previous
        if old and v and old['view'] and raw['levels_completed']==old['raw']['levels_completed'] and old['action']!=0:
            before=old['view'];delta=minus(v['body']['box'][:2],before['body']['box'][:2]);a=old['action']
            self.history.append(dict(before=old['raw'],action=a,after=copy.deepcopy(raw)))
            if delta!=(0,0):
                if (delta[0]==0) != (delta[1]==0):
                    earlier=self.motions.get(a)
                    if earlier is None:self.motions[a]=dict(delta=delta,support=old['t'])
                    elif tuple(earlier['delta'])!=delta:self.motions.pop(a,None)
                before_pos=self.positions(before);after_pos=self.positions(v)
                movers=[p for p in before_pos if p not in after_pos and plus(p,delta) in after_pos]
                if len(movers)==1 and len(before_pos&after_pos)==len(before_pos)-1:
                    offset=minus(movers[0],before['body']['box'][:2]);self.held=offset
                    self.attachment=dict(support=old['t'],offset=offset)
                elif old['tag']=='verify_drop':self.held=None;self.attachment=None
                elif self.held is not None:self.held=None;self.attachment=None
                if old['tag'] in ('verify_pick','verify_drop'):self.mode=None
            elif a in self.motions:
                self.blocked.add((tuple(before['body']['box'][:2]),a,tuple(sorted(self.positions(before)))))
            if old['tag']=='pickup':self.mode='verify_pick'
            elif old['tag']=='release':self.mode='verify_drop'
        if v and self.goal is None and len(v['containers'])==1:
            container=v['containers'][0]
            self.goal=dict(box=tuple(container['box']),inner_ink=container['inner_ink'],frame_ink=container['frame_ink'],observed_at=self.t,hypothesis='tile_container_with_repeated_objects')

    def slots(self):
        if self.goal is None:return set()
        y,x,h,w=self.goal['box'];n=self.signature[0]
        return {(a,b) for a in range(y,y+h,n) for b in range(x,x+w,n)}

    def route(self,v,target,offset=None):
        at=tuple(v['body']['box'][:2]);cargo=self.positions(v);n=v['n']
        if offset is not None:cargo.discard(plus(at,offset))
        previous={at:None};todo=deque([at]);height=64;width=64
        while todo and len(previous)<2500:
            p=todo.popleft()
            if p==target:break
            for a,m in sorted(self.motions.items()):
                q=plus(p,m['delta']);held=None if offset is None else plus(q,offset)
                if q in previous or q in cargo or not(0<=q[0]<=height-n and 0<=q[1]<=width-n):continue
                if held is not None and (held in cargo or not(0<=held[0]<=height-n and 0<=held[1]<=width-n)):continue
                if (p,a,tuple(sorted(self.positions(v)))) in self.blocked:continue
                previous[q]=(p,a);todo.append(q)
        if target not in previous:return None
        out=[];p=target
        while previous[p] is not None:p,a=previous[p];out.append(a)
        return out[::-1]

    def answer(self,raw,v,action,tag):
        certificate=dict(kind='carry_causal_action',tag=tag,goal=copy.deepcopy(self.goal),body=None if v is None else copy.deepcopy(v['body']),
            motions=copy.deepcopy(self.motions),attachment=copy.deepcopy(self.attachment),goal_is_hypothesis=True)
        response=dict(done=False,action=action,data={},certificate=certificate)
        self.previous=dict(raw=copy.deepcopy(raw),view=copy.deepcopy(v),action=action,t=self.t,tag=tag)
        self.trials[action]+=1;self.t+=1;return response

    def respond(self,raw):
        assert set(raw)<= {'frame','state','available_actions','levels_completed'}
        v=self.view(raw);self.record(raw,v)
        if raw['state']=='WIN':return dict(done=True,action=None,data={})
        if raw['state']=='GAME_OVER':
            if not self.retain:
                self.goal=None;self.motions={};self.blocked=set();self.attachment=None;self.trials.clear()
            self.held=None;self.mode=None;self.target=None
            return self.answer(raw,v,0,'reset_after_failure')
        if v is None:
            return self.prior.respond(raw) if self.prior and not self.active else dict(done=True,action=None,data={})
        self.active=True;allowed=raw['available_actions'];at=tuple(v['body']['box'][:2])
        if len(self.motions)<4:
            a=min(allowed,key=lambda a:(a in self.motions,self.trials[a],a))
            return self.answer(raw,v,a,'motion_inquiry')
        aux=[a for a in allowed if a not in self.motions]
        if not aux:return dict(done=True,action=None,data={})
        if self.goal is None:
            self.no_goal_steps+=1
            if self.no_goal_steps>12:return dict(done=True,action=None,data={})
            return self.answer(raw,v,min(allowed,key=lambda a:(self.trials[a],a)),'goal_unknown_probe')
        if self.mode in ('verify_pick','verify_drop'):
            offset=self.held
            if offset is None and self.target is not None:offset=minus(self.target,at)
            choices=[]
            for a,m in self.motions.items():
                route=self.route(v,plus(at,m['delta']),self.held)
                if route and len(route)==1:
                    away=0 if offset and sum(x*y for x,y in zip(offset,m['delta']))<0 else 1
                    choices.append((away,a))
            if choices:return self.answer(raw,v,min(choices)[1],self.mode)
            self.mode=None
        slots=self.slots();cargo=self.positions(v)
        if self.held is not None:
            held=plus(at,self.held);loose=cargo-{held};choices=[]
            if held in slots:return self.answer(raw,v,aux[0],'release')
            for slot in sorted(slots-loose):
                route=self.route(v,minus(slot,self.held),self.held)
                if route is not None:choices.append((len(route),slot,route))
            if choices:
                route=min(choices)[2]
                if route:return self.answer(raw,v,route[0],'carry_toward_goal_hypothesis')
        else:
            choices=[];y,x,h,w=self.goal['box'];perpendicular=0 if w>h else 1
            for target in sorted(cargo-slots):
                for a,m in sorted(self.motions.items()):
                    if m['delta'][perpendicular]==0:continue
                    approach=minus(target,m['delta']);route=self.route(v,approach)
                    if route is not None:choices.append((len(route),target,a,route))
            if choices:
                _,target,a,route=min(choices);self.target=target
                if route:return self.answer(raw,v,route[0],'approach_object')
                old=self.previous
                if old and old['action']==a and old['tag']=='orient_toward_object':
                    return self.answer(raw,v,aux[0],'pickup')
                return self.answer(raw,v,a,'orient_toward_object')
        # A completed spatial arrangement without actual progress refutes the
        # current interpretation; it must never manufacture a solved outcome.
        return dict(done=True,action=None,data={})
