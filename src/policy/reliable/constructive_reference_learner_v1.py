"""Try constructing visible reference programs; preserve failed physical trials.

A matching hollow control and frame suggest a possible reference operation.
This is a tentative visual analogy, never a supplied action effect or goal.
"""
from collections import Counter,defaultdict
import copy
from centered_word_learner_v2 import Learner as Base
from centered_symbol_rows_v1 import tokens
from centered_word_geometry_v2 import frames,enclosed,border
from literal_word_rows import center,values,contains
from visual_transform_learner import public,digest


def inventory(frame):
    items=tokens(frame);out=[]
    for box,ink in frames(frame):
        axis=1 if box[3]>box[2] else 0;bins=defaultdict(list)
        for item in items:
            c=item['core']
            if enclosed(c,box):bins[c[1-axis],c[2],c[3]].append(item)
        options=[]
        for group in bins.values():
            group.sort(key=lambda t:t['core'][axis]);places=[t['core'][axis] for t in group]
            if 3<=len(group)<=8 and len(set(b-a for a,b in zip(places,places[1:])))==1:options.append(group)
        if len(options)==1:out.append(dict(box=box,color=ink,axis=axis,cells=tuple(t['core'] for t in options[0]),tokens=tuple(options[0])))
    return out


def ring_present(frame,cell,ink):
    y,x,h,w=cell
    return y>0 and x>0 and y+h<len(frame) and x+w<len(frame[0]) and all(frame[v][u]==ink for v,u in border((y-1,x-1,h+2,w+2)))


class Learner(Base):
    def __init__(self,*,retain=True):
        super().__init__(retain=retain)
        self.reference_groups={};self.reference_controls={};self.reference_trials=[]

    def observe(self,raw,action=None,data=None):
        obs=public(raw);old=self.previous;pending=copy.deepcopy(self.pending)
        super().observe(obs,action,data)
        if old and pending and pending.get('reference_plan') and action is not None and self.history:
            p=pending['reference_plan']
            if old['state']==obs['state']=='NOT_FINISHED' and old['levels_completed']==obs['levels_completed']:
                point=(data or {}).get('x'),(data or {}).get('y')
                self.reference_trials.append(dict(index=len(self.history)-1,phase=pending['phase'],operation=p['operation'],
                    point=point,plan_key=self.plan_key(p),changed=old['frame']!=obs['frame'],
                    before_values=values(old['frame'],p['leaves']),after_values=values(obs['frame'],p['leaves'])))
        if obs['state']!='NOT_FINISHED':return
        index=len(self.history)
        for group in inventory(obs['frame']):
            self.reference_groups.setdefault(group['box'],dict(observed_at=index,group=copy.deepcopy(group)))
        for token in tokens(obs['frame']):
            if token['hollow']:
                self.reference_controls.setdefault((token['core'],token['color']),dict(observed_at=index,token=copy.deepcopy(token)))

    @staticmethod
    def plan_key(p):
        return p['parent']['group']['box'],p['child']['group']['box'],p['slot'],p['source'],p['channel'],p['word']

    def plans(self,obs):
        result=[];f=obs['frame']
        for parent in self.reference_groups.values():
            a=parent['group']
            for child in self.reference_groups.values():
                b=child['group'];n=len(a['cells'])+len(b['cells'])-1
                if a['box']==b['box'] or not 3<=n<=8 or set(a['cells'])&set(b['cells']):continue
                controls=[v for (core,ink),v in self.reference_controls.items() if ink==b['color']
                    and not any(contains(c,center(core)) for c in a['cells']+b['cells']) and ring_present(f,core,ink)]
                if not controls:continue
                for (source,channel,word),index in self.sources.items():
                    if len(source)!=n or self.edited[source] or set(source)&set(a['cells']+b['cells']):continue
                    remembered=self.history[index]['before'] if index<len(self.history) else obs
                    # Erased examples remain available and get priority over
                    # a currently visible palette. This remains a hypothesis.
                    erased=values(f,source)!=values(remembered['frame'],source)
                    for slot in range(len(a['cells'])):
                        leaves=a['cells'][:slot]+b['cells']+a['cells'][slot+1:]
                        if values(f,leaves) is None:continue
                        p=dict(parent=copy.deepcopy(parent),child=copy.deepcopy(child),slot=slot,leaves=leaves,
                            source=source,channel=channel,word=word,observed_at=index,reference_control=copy.deepcopy(controls[0]))
                        goal=dict(target=leaves,source=source,channel=channel,word=word,observed_at=index)
                        tried=sum(self.strategy_failures[self.goal_key(goal),action] for action in (5,7,1,2,3,4))
                        failures=sum(t['phase']=='apply' and t['before_values']==t['after_values'] for t in self.reference_trials if t['plan_key']==self.plan_key(p))
                        sizes=[t['box'][2] for t in b['tokens']];small=min(sizes)
                        # A visually enlarged prefilled symbol is a tentative
                        # constraint, not proof that the symbol is immutable.
                        mismatch=sum(t['box'][2]>small and t['value']!=word[slot+k] for k,t in enumerate(b['tokens']))
                        result.append(((tried,failures//4,mismatch,not erased,channel=='fill',index,source,slot,a['box'],b['box']),p))
        return [p for _,p in sorted(result,key=lambda v:v[0])]

    def propose(self,raw):
        obs=public(raw)
        if obs['state']!='NOT_FINISHED':return super().propose(obs)
        if self.queued and self.queued.get('reference_plan'):
            q=self.queued
            return dict(kind='literal_tool_word_attempt',context=digest(obs),phase='apply',action=6,
                data=dict(x=q['point'][0],y=q['point'][1]),goal=copy.deepcopy(q['goal']),evidence=[],
                selection=copy.deepcopy(q['selection']),predicted_token=None,reference_plan=copy.deepcopy(q['reference_plan']),
                scope='Test the selected operation and measure its actual outcome; no success or constant effect is asserted.')
        if self.queued:return super().propose(obs)
        candidates=self.plans(obs)
        if not candidates:return super().propose(obs)
        p=candidates[0];parent=p['parent']['group'];child=p['child']['group'];slot=p['slot'];f=obs['frame']
        base=dict(kind='literal_tool_word_attempt',context=digest(obs),evidence=[],predicted_token=None,
            scope='A tentative constructed-reference program from retained visible geometry and examples. Test every operation; preserve failures.')
        if not ring_present(f,parent['cells'][slot],child['color']):
            p['operation']='insert';point=center(p['reference_control']['token']['core']);follow=center(parent['cells'][slot])
            return dict(base,phase='select',action=6,data=dict(x=point[0],y=point[1]),goal=None,
                target=parent['cells'],followup=follow,reference_plan=p)
        goal=dict(target=p['leaves'],source=p['source'],channel=p['channel'],word=p['word'],observed_at=p['observed_at'])
        current=values(f,p['leaves']);p['operation']='paint'
        if current==p['word']:
            choices=[a for a in (5,7,1,2,3,4) if a in obs['available_actions'] and not self.strategy_failures[self.goal_key(goal),a]]
            if choices:
                p['operation']='submit'
                return dict(base,phase='submit',action=choices[0],data={},goal=goal,reference_plan=p)
        mismatch=[i for i,(a,b) in enumerate(zip(current,p['word'])) if a!=b]
        if not mismatch:return super().propose(obs)
        k=mismatch[0];desired=p['word'][k];point=center(p['leaves'][k]);controls=[]
        for token in tokens(f):
            c=center(token['core'])
            if any(contains(box,c) for box in parent['cells']+child['cells']):continue
            if token['hollow'] or token['value']!=desired:continue
            # Actual same-point failures lower a control's priority. The
            # visible color match itself remains only an exploratory analogy.
            trials=sum(t['phase']=='apply' and t['point']==point and t['plan_key']==self.plan_key(p)
                for t in self.reference_trials)
            controls.append((self.pair_trials[p['leaves'],c],trials,c))
        if not controls:return super().propose(obs)
        _,_,control=min(controls);p['paint_token']=k;p['paint_control']=control
        return dict(base,phase='select',action=6,data=dict(x=control[0],y=control[1]),goal=goal,
            target=p['leaves'],followup=point,reference_plan=p)

    def commit(self,c):
        super().commit(c)
        if c['phase']=='select' and c.get('reference_plan'):
            self.queued['reference_plan']=copy.deepcopy(c['reference_plan'])
