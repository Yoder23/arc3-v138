"""Learn controllable objects and action geometry from consecutive visible frames.

No game identifiers, action-direction table, goal-color convention or hidden
collision map. Navigation is used only after observing repeatable translation.
"""
import hashlib,heapq,math
from collections import Counter,defaultdict
import numpy as np
from scipy import ndimage as ndi


def objects(frame):
    a=np.asarray(frame,dtype=np.int16);bg=int(np.bincount(a.ravel()).argmax());result=[]
    for color in np.unique(a):
        if color==bg:continue
        labels,n=ndi.label(a==color)
        for idx,sl in enumerate(ndi.find_objects(labels),1):
            if sl is None:continue
            patch=labels[sl]==idx;size=int(patch.sum());h,w=patch.shape
            if not 1<=size<=256 or max(h,w)>20:continue
            y,x=sl[0].start,sl[1].start
            signature=(int(color),h,w,hashlib.sha256(patch.tobytes()).hexdigest()[:12])
            result.append({'signature':signature,'y':y,'x':x,'h':h,'w':w,'size':size,'mask':patch})
    return result


class Navigator:
    def __init__(self):
        self.effects=defaultdict(Counter);self.support=Counter();self.actions=Counter();self.previous=None
        self.identity=None;self.position=None;self.blocked=Counter();self.visits=Counter();self.floor=Counter();self.walls=Counter();self.local_trials=Counter()
        self.step=0;self.last_action=None;self.level=0;self.target=None;self.proposals=0;self.matches=0;self.revisions=0
        self.current_objects=[];self.frame=None;self.plans=0;self.target_visits=Counter();self.successful_types=Counter()

    def observe(self,frame,action=None,progress=False,reset=False):
        self.step+=1;a=np.asarray(frame,dtype=np.int16);current=objects(a);self.current_objects=current;self.frame=a
        if progress:
            if self.target is not None:self.successful_types[self.target[0]]+=1
            self.blocked.clear();self.visits.clear();self.target_visits.clear();self.floor.clear();self.walls.clear();self.local_trials.clear();self.target=None;self.identity=None
        if self.previous is not None and action in (1,2,3,4,5,7) and not progress and not reset:
            old_frame,old_objects=self.previous
            self.actions[action]+=1
            oldgroups=defaultdict(list);newgroups=defaultdict(list)
            for ob in old_objects:oldgroups[ob['signature']].append(ob)
            for ob in current:newgroups[ob['signature']].append(ob)
            for sig,before in oldgroups.items():
                after=newgroups.get(sig,[])
                # Ambiguous identity is not silently converted into supervision.
                if len(before)!=1 or len(after)!=1:continue
                old,new=before[0],after[0];dy,dx=new['y']-old['y'],new['x']-old['x']
                if 0<abs(dy)+abs(dx)<=16 and (dy==0 or dx==0):
                    self.effects[(sig,action)][(dy,dx)]+=1;self.support[sig]+=1;self.matches+=1
                if self.identity==sig:
                    pos=(old['y'],old['x']);edge=(pos,action)
                    self.local_trials[edge]+=1
                    if dy or dx:
                        if self.blocked[edge]:self.revisions+=1
                        self.blocked[edge]=0
                        yy,xx=new['y'],new['x'];patch=old_frame[yy:yy+new['h'],xx:xx+new['w']]
                        for c,n in zip(*np.unique(patch,return_counts=True)):
                            if int(c)!=sig[0]:self.floor[int(c)]+=int(n)
                    else:
                        self.blocked[edge]+=1
                        effect=self.effect(sig,action)
                        if effect is not None:
                            yy,xx=old['y']+effect[0],old['x']+effect[1]
                            if 0<=yy<=a.shape[0]-old['h'] and 0<=xx<=a.shape[1]-old['w']:
                                patch=old_frame[yy:yy+old['h'],xx:xx+old['w']]
                                for c,n in zip(*np.unique(patch,return_counts=True)):
                                    if int(c)!=sig[0]:self.walls[int(c)]+=int(n)
            choices=[]
            for ob in current:
                sig=ob['signature']
                if len(newgroups[sig])!=1:continue
                learned=[self.effect(sig,k) for k in (1,2,3,4,5,7)]
                vectors=[v for v in learned if v is not None]
                # Require repeatability plus independent or opposing controls.
                # Opposed effects identify an actor in a straight corridor;
                # monotonic one-axis counters still fail this criterion.
                two_axes=any(v[0] for v in vectors) and any(v[1] for v in vectors)
                opposed=any(u[0]*v[0]+u[1]*v[1]<0 for u in vectors for v in vectors)
                if len(vectors)>=2 and (two_axes or opposed):
                    choices.append((len(vectors),self.support[sig],sig,ob))
            if choices:
                _,_,sig,ob=max(choices,key=lambda q:(q[0],q[1],repr(q[2])))
                if self.identity!=sig:self.identity=sig;self.target=None
        controlled=[o for o in current if o['signature']==self.identity]
        self.position=controlled[0] if len(controlled)==1 else None
        if self.position:
            pos=(self.position['y'],self.position['x']);self.visits[pos]+=1
            if self.target is not None:
                _,ty,tx=self.target
                if abs(pos[0]-ty)<=max(1,self.position['h']//2) and abs(pos[1]-tx)<=max(1,self.position['w']//2):
                    self.target_visits[self.target]+=1;self.target=None
        self.previous=None if reset else (a.copy(),current)

    def effect(self,sig,action):
        count=self.effects.get((sig,action))
        if not count:return None
        vector,n=count.most_common(1)[0]
        return vector if n>=2 and n>=.7*sum(count.values()) else None

    def choose(self,legal):
        if self.position is None:return None
        ob=self.position;start=(ob['y'],ob['x']);sig=ob['signature'];a=self.frame
        moves={k:self.effect(sig,k) for k in legal if k in (1,2,3,4,5,7)}
        known={k:v for k,v in moves.items() if v is not None}
        if len(known)<2:return None
        # Test unknown controls occasionally; a failed navigation model can
        # therefore discover an interaction or a different movement mode.
        unknown=[k for k,v in moves.items() if v is None]
        untested_here=[k for k in unknown if not self.local_trials[(start,k)]]
        if untested_here:
            self.proposals+=1
            return min(untested_here,key=lambda k:(self.actions[k],k))
        if unknown and self.step%7==0:return min(unknown,key=lambda k:(self.actions[k],k))
        floor_colors={c for c,n in self.floor.items() if n>self.walls[c]}
        bad_colors={c for c,n in self.walls.items() if n>=4 and n>2*self.floor[c]}
        targets=[]
        for other in self.current_objects:
            if other['signature']==sig:continue
            key=(other['signature'],other['y']+(other['h']-ob['h'])//2,other['x']+(other['w']-ob['w'])//2)
            if self.target_visits[key]<2:targets.append(key)
        # Plan through the visible image using learned effects and accumulated
        # collision evidence. Uncertain terrain remains available at a cost.
        queue=[(0.,start,None)];best={start:0.};reachable=[];expansions=0
        while queue and expansions<320:
            cost,pos,first=heapq.heappop(queue)
            if cost>best[pos]+1e-9:continue
            expansions+=1
            if first is not None:
                novelty=3/(1+self.visits[pos])
                utility=novelty-.12*cost
                if self.target is not None:
                    _,ty,tx=self.target;utility+=4/(1+.2*(abs(ty-pos[0])+abs(tx-pos[1])))
                for key in targets:
                    _,ty,tx=key;distance=abs(ty-pos[0])+abs(tx-pos[1])
                    if distance<=max(1,min(ob['h'],ob['w'])//2):
                        utility+=5/(1+self.target_visits[key])+2*self.successful_types[key[0]]
                reachable.append((utility,-cost,-self.visits[pos],pos,first))
            for action,(dy,dx) in sorted(known.items()):
                nxt=(pos[0]+dy,pos[1]+dx);yy,xx=nxt
                if not (0<=yy<=a.shape[0]-ob['h'] and 0<=xx<=a.shape[1]-ob['w']):continue
                if self.blocked[(pos,action)]>=2:continue
                patch=a[yy:yy+ob['h'],xx:xx+ob['w']][ob['mask']]
                values=set(map(int,patch))-{sig[0]}
                if values&bad_colors:continue
                risk=.4*len(values-floor_colors)
                nc=cost+1+risk+.15*min(8,self.visits[nxt])
                if nc<best.get(nxt,float('inf')):
                    best[nxt]=nc;heapq.heappush(queue,(nc,nxt,action if first is None else first))
        if not reachable:return None
        _,_,_,dest,chosen=max(reachable)
        if self.target is None:
            close=sorted(targets,key=lambda key:abs(key[1]-dest[0])+abs(key[2]-dest[1]))
            if close and abs(close[0][1]-dest[0])+abs(close[0][2]-dest[1])<=max(ob['h'],ob['w']):self.target=close[0]
        # Reopen a repeatedly failing target rather than persisting forever.
        if self.visits[start]>12 and self.step%16==0:
            if self.target is not None:self.target_visits[self.target]+=1
            self.target=None;self.revisions+=1
        self.proposals+=1;self.plans+=expansions;return chosen

    def diagnostics(self):
        return {'object_correspondences':self.matches,'controlled_object':repr(self.identity),'navigation_choices':self.proposals,'planning_expansions':self.plans,'world_model_revisions':self.revisions,'position_states':len(self.visits),'effect_models':len(self.effects)}
