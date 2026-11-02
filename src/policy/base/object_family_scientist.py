"""Legal-observation scientist: episodic graph, intervention novelty and N2B transfer.

No environment ID, hidden goals, scorer baselines or game-source access. The
engineered feature adapter is intentionally documented as a transfer hypothesis.
"""
import argparse,sys,json,hashlib,math
from collections import Counter,deque
from pathlib import Path
import numpy as np
from progress_memory import ProgressMemory
from memory import AssociativeMemory
from grounding import GroundedEffects
from navigation import Navigator,objects as component_objects
from causal_clicks import CausalClicks

SLOTS={1:0,2:1,3:2,4:3,5:4,7:5}


def perception(frame):
    a=np.asarray(frame,dtype=np.int16);bg=int(np.bincount(a.ravel()).argmax())
    cells=np.argwhere(a!=bg)
    if len(cells):
        y,x=cells.mean(0);mass=len(cells)/a.size
    else:y,x,mass=0.,0.,0.
    features=np.array([5+37*x/max(1,a.shape[1]-1),5+37*y/max(1,len(a)-1),5+37*mass])
    # Coarse color distribution per 4x4 patch suppresses one-pixel counters and
    # tracks larger visible spatial changes without an engineered game crop.
    coarse=[]
    for y in range(0,len(a),4):
        for x in range(0,a.shape[1],4):
            block=a[y:y+4,x:x+4];coarse.append(int(np.bincount(block.ravel()).argmax()))
    state=hashlib.sha256(bytes(coarse)).hexdigest()[:24]
    return a,features,state


def clicks(a):
    bg=int(np.bincount(a.ravel()).argmax());seen=set();objects=[]
    for y,x in np.argwhere(a!=bg):
        y,x=int(y),int(x)
        if (y,x) in seen:continue
        todo=[(y,x)];seen.add((y,x));cells=[]
        while todo:
            r,c=todo.pop();cells.append((r,c))
            for dy,dx in ((1,0),(-1,0),(0,1),(0,-1)):
                yy,xx=r+dy,c+dx
                if 0<=yy<len(a) and 0<=xx<a.shape[1] and (yy,xx) not in seen and a[yy,xx]==a[y,x]:
                    seen.add((yy,xx));todo.append((yy,xx))
        if 2<=len(cells)<=a.size//3:
            center=np.mean(cells,0);r,c=min(cells,key=lambda p:float(np.sum((np.asarray(p)-center)**2)))
            objects.append((-len(cells),r,c))
    points=[(c,r) for _,r,c in sorted(objects)[:32]]
    points += [(x,y) for y in range(4,64,8) for x in range(4,64,8)]
    return list(dict.fromkeys(points))


class Scientist:
    def __init__(self,arm,weights=None,grounded=True):
        self.progress_memory=ProgressMemory();self.grounding=GroundedEffects() if grounded else None;self.last_frame=None;self.last_ground_action=None;self.last_ground_state=None
        self.arm=arm;self.brain=None;self.hidden=None;self.navigator=Navigator() if arm in ('navigation','causal') else None;self.causal=CausalClicks() if arm=='causal' else None
        if arm=='hybrid':
            global torch
            import torch
            from brain import Brain
            torch.set_num_threads(1);self.brain=Brain('hybrid')
            checkpoint=torch.load(weights,map_location='cpu',weights_only=False)
            self.brain.load_state_dict(checkpoint['state_dict'] if 'state_dict' in checkpoint else checkpoint['weights'])
            self.brain.eval();self.hidden=self.brain.initial(1)
        self.memory=AssociativeMemory();self.graph={};self.options={};self.trials=Counter();self.visits=Counter()
        self.global_trials=Counter();self.prev=None;self.step=0;self.level=0;self.successes=[]
        self.events=Counter();self.surprise=0.;self.stagnation=0;self.reset_count=0
        self.family_trials=Counter();self.family_steps=0;self.component_trials=Counter();self.component_positions={};self.component_stability=Counter();self.click_objects=[]
        self.goal_use=0;self.forecast_use=0;self.frontier_routes=0;self.trace_hash=hashlib.sha256()

    def observe_components(self,a,progress):
        if progress:self.component_trials.clear();self.component_positions={};self.component_stability.clear()
        parts=component_objects(a);counts=Counter(o['signature'] for o in parts);current={}
        for o in parts:
            key=(o['signature'],None if counts[o['signature']]==1 else (o['y'],o['x']))
            o['click_key']=key;position=(o['y'],o['x']);current[key]=position
            self.component_stability[key]=self.component_stability[key]+1 if self.component_positions.get(key)==position else 0
        self.component_positions=current;self.click_objects=parts

    def component_probe(self):
        candidates=[o for o in self.click_objects if self.component_trials[o['click_key']]<2]
        if not candidates:return None
        o=min(candidates,key=lambda o:(self.component_trials[o['click_key']],-min(3,self.component_stability[o['click_key']]),-o['size'],repr(o['click_key'])))
        cells=np.argwhere(o['mask']);center=cells.mean(axis=0)
        y,x=min(map(tuple,cells.tolist()),key=lambda p:(float(np.sum((np.asarray(p)-center)**2)),p))
        return (6,int(o['x']+x),int(o['y']+y))

    def base(self,pos,delta,last,reset):
        if self.brain is None:return np.zeros((6,3))
        x=np.zeros(20,dtype=np.float32);x[:3]=(pos-24)/24;x[3:6]=delta/4
        x[6:9]=1
        if last in SLOTS:x[12+SLOTS[last]]=1
        x[-2]=1;x[-1]=reset
        with torch.no_grad():out,self.hidden=self.brain.step(torch.from_numpy(x)[None],self.hidden)
        return out[0].numpy().astype(np.float64)

    def route_frontier(self,current):
        q=deque([(current,[])]);seen={current}
        while q and len(seen)<=512:
            state,path=q.popleft()
            if path and any(not self.trials[(state,a)] for a in self.options.get(state,())):return path[0]
            for action,dest in sorted(self.graph.get(state,{}).items()):
                if dest not in seen and dest!=state:
                    seen.add(dest);q.append((dest,path+[action]))
        return None

    def respond(self,obs):
        if set(obs)!={'frame','available_actions','state','levels_completed'}:raise ValueError('Illegal observation fields')
        self.step+=1;self.progress_memory.observe(obs)
        if obs['state']=='WIN':return {'done':True,'diagnostics':self.diagnostics()}
        a,pos,state=perception(obs['frame']);state=str(obs['levels_completed'])+':'+state
        self.observe_components(a,obs['levels_completed']>self.level)
        if self.navigator is not None:
            self.navigator.observe(a,self.prev[2][0] if self.prev else None,progress=obs['levels_completed']>self.level,reset=obs['state'] in ('GAME_OVER','NOT_PLAYED'))
        if self.causal is not None:
            self.causal.observe(a,self.prev[2] if self.prev else None,progress=obs['levels_completed']>self.level,reset=obs['state'] in ('GAME_OVER','NOT_PLAYED'))
        if self.grounding is not None and self.last_frame is not None and self.last_ground_action is not None:
            self.grounding.observe(self.last_frame,self.last_ground_action,a,self.last_ground_state)
        delta=np.zeros(3);last=None;progress=obs['levels_completed']>self.level
        if self.prev is not None:
            old,oldpos,last,pred=self.prev;delta=pos-oldpos
            self.graph.setdefault(old,{})[last]=state
            if old==state:self.stagnation+=1
            else:self.stagnation=0
            if last[0] in SLOTS and not progress and obs['state']!='GAME_OVER':
                index=SLOTS[last[0]]
                event=self.memory.observe(oldpos,index,delta,np.ones(3,dtype=bool),self.step,pred)
                self.events[event['event']]+=1;self.surprise=.9*self.surprise+.1*event['prior_error']
            if progress:
                # Progress gives a hypothesis about an action's useful visible
                # effect. It is not an externally supplied goal or solved recipe.
                self.successes.append((oldpos.copy(),last,delta.copy()))
                self.family_trials.clear();self.family_steps=0
                self.graph={};self.options={};self.trials=Counter();self.visits=Counter()
                self.memory=AssociativeMemory()
                if self.brain is not None:self.hidden=self.brain.initial(1)
        self.level=obs['levels_completed'];self.visits[state]+=1
        last_id=last[0] if last else None
        prior=self.base(pos,delta,last_id,progress)
        predicted,variance,support=self.memory.predict(pos,prior)
        legal=sorted(v for v in obs['available_actions'] if v!=0)
        if obs['state'] in ('GAME_OVER','NOT_PLAYED') or not legal:
            self.prev=None;self.last_frame=None;self.last_ground_action=None;self.reset_count+=1
            return {'done':False,'action':0,'data':{},'diagnostics':self.diagnostics()}
        actions=[(v,-1,-1) for v in legal if v!=6]
        if 6 in legal:actions += [(6,x,y) for x,y in clicks(a)]
        self.options[state]=actions
        learned_click_bias=self.progress_memory.biases(obs['frame'],actions)
        untried=[c for c in actions if self.trials[(state,c)]==0]
        route=None if untried else self.route_frontier(state)
        if route in actions:
            chosen=route;self.frontier_routes+=1
        else:
            scored=[]
            for choice in actions:
                action=choice[0];n=self.trials[(state,choice)]
                target=self.graph.get(state,{}).get(choice)
                score=5/(1+n)+1/math.sqrt(1+self.global_trials[choice])+learned_click_bias.get(choice,0.)/(1+n)
                if target is not None:score+=1/(1+self.visits[target])-(2 if target==state else 0)
                if self.grounding is not None:score+=self.grounding.value(a,choice)
                if action in SLOTS:
                    index=SLOTS[action]
                    # A small prior influences which unknown intervention comes
                    # first. Sparse evidence is retained despite model uncertainty.
                    score+=.08*min(5.,float(np.linalg.norm(predicted[index])))
                    score+=.15/math.sqrt(1+float(support[index].mean()))
                    self.forecast_use+=int(self.brain is not None)
                    for oldpos,oldchoice,effect in self.successes[-8:]:
                        similarity=math.exp(-float(np.mean(((oldpos-pos)/12)**2)))
                        score+=.2*similarity*math.exp(-float(np.mean((predicted[index]-effect)**2)))
                        self.goal_use+=1
                # Stable hashed tie-break instead of global RNG/call-order effects.
                jitter=int(hashlib.sha256((state+repr(choice)).encode()).hexdigest()[:8],16)/2**32
                scored.append((score+.025*jitter,choice))
            chosen=max(scored)[1]
            # A click has many coordinate choices but is one input modality.
            # Balance only the initial discovery budget; real planners below
            # still select their supported actions and observe actual outcomes.
            if 6 in legal and len(legal)>1 and self.family_steps<96:
                best={family:max(item for item in scored if item[1][0]==family) for family in legal}
                family=min(legal,key=lambda a:(self.family_trials[a],-best[a][0],a))
                chosen=best[family][1]
                if family==6:chosen=self.component_probe() or chosen
        if self.navigator is not None:
            proposal=self.navigator.choose(legal)
            if proposal in legal and proposal!=6:chosen=(proposal,-1,-1)
        if self.causal is not None:
            proposal=self.causal.choose(legal)
            if proposal is not None:chosen=proposal
        self.progress_memory.selected+=int(learned_click_bias.get(chosen,0.)>0)
        self.progress_memory.remember(obs,chosen,self.step)
        if chosen[0]==6:
            for o in self.click_objects:
                yy,xx=chosen[2]-o['y'],chosen[1]-o['x']
                if 0<=yy<o['h'] and 0<=xx<o['w'] and o['mask'][yy,xx]:
                    self.component_trials[o['click_key']]+=1
        self.family_trials[chosen[0]]+=1;self.family_steps+=1
        self.trials[(state,chosen)]+=1;self.global_trials[chosen]+=1
        self.last_frame=a.copy();self.last_ground_action=chosen;self.last_ground_state=state
        self.prev=(state,pos.copy(),chosen,predicted.copy())
        self.trace_hash.update(json.dumps([state,chosen],separators=(',',':')).encode())
        return {'done':False,'action':chosen[0],'data':{'x':chosen[1],'y':chosen[2]} if chosen[0]==6 else {},
            'diagnostics':self.diagnostics()}

    def diagnostics(self):
        return {**self.progress_memory.diagnostics(),**(self.navigator.diagnostics() if self.navigator else {}),**(self.causal.diagnostics() if self.causal else {}),'grounded_episodes':len(self.grounding.episodes) if self.grounding else 0,'grounded_comparisons':self.grounding.used if self.grounding else 0,'steps':self.step,'states':len(self.visits),'memory_records':len(self.memory.records),
                'contexts':len(self.memory.contexts),'events':dict(self.events),'surprise':self.surprise,
                'successful_effect_hypotheses':len(self.successes),'goal_comparisons':self.goal_use,
                'neural_forecast_comparisons':self.forecast_use,'frontier_routes':self.frontier_routes,
                'resets':self.reset_count,'action_digest':self.trace_hash.hexdigest()}


def main():
    p=argparse.ArgumentParser();p.add_argument('--arm',choices=['zero','hybrid','navigation','causal'],required=True);p.add_argument('--weights');args=p.parse_args()
    agent=Scientist(args.arm,args.weights)
    # Warm up PyTorch lazy inference before denying file/network/process access.
    agent.base(np.array([24.,24.,24.]),np.zeros(3),None,True)
    if agent.brain is not None:agent.hidden=agent.brain.initial(1)
    import builtins,io,os,socket
    def deny(*a,**kw):raise PermissionError('Legal observation stream only')
    builtins.open=io.open=os.open=deny;socket.socket=deny
    def audit(event,args):
        if event in ('open','os.listdir','os.scandir','subprocess.Popen','os.system') or event.startswith('socket.'):deny()
    sys.addaudithook(audit)
    for line in sys.stdin:print(json.dumps(agent.respond(json.loads(line))),flush=True)

if __name__=='__main__':main()
