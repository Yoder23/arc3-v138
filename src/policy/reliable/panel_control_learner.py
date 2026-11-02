"""Learn editable glyph sequences, cyclic edits and selection from actual outcomes."""
import copy
from collections import Counter,defaultdict,deque
from panel_hypotheses_v2 import candidates,rectangles,glyphs,transformed,digest,recognize

def identity(mask):return min(transformed(mask,k,f) for k in range(4) for f in (False,True))
class Learner:
    def __init__(self):
        self.previous=None;self.snapshot=None;self.scenes=[];self.hypotheses=[];self.rows={};self.edit_rows=[];self.select_rows=[]
        self.anchor=None;self.current=None;self.between=[];self.counts=Counter();self.pending=None;self.outcomes=[]
    def scene(self,obs):
        parsed=candidates(obs);hyp=parsed['proposals']
        if hyp:self.hypotheses=copy.deepcopy(hyp)
        rectangles_by_box={r['box']:r for r in parsed['rectangles']};scenes=[]
        for p in self.hypotheses:
            box=p['target_box'];source=p['source_box'];right=rectangles_by_box.get(box);left=rectangles_by_box.get(source)
            if right is None or left is None:continue
            gs=glyphs(right);ss=glyphs(left)
            if len(gs)!=len(p['expected']) or len(ss)!=len(gs):continue
            mapping={e['source_mask']:e['target_mask'] for e in p['examples']};recognized=[recognize(g['mask'],mapping) for g in ss]
            if any(v is None for v in recognized):continue
            proposal=copy.deepcopy(p);proposal.update(observation=digest(obs),expected=tuple(v['expected'] for v in recognized),actual=tuple(g['mask'] for g in gs),recognition=recognized,points=tuple(g['point'] for g in gs))
            proposal['mismatches']=[i for i,(g,e) in enumerate(zip(gs,proposal['expected'])) if identity(g['mask'])!=identity(e)]
            scenes.append(dict(box=box,source_box=source,classes=tuple(identity(g['mask']) for g in gs),expected=tuple(identity(g) for g in proposal['expected']),proposal=proposal))
        return scenes
    def observe(self,obs,action=None):
        old=self.previous;prior=self.snapshot;old_scenes=self.scenes;intent=self.pending;self.pending=None
        progress=old is not None and (obs['levels_completed']!=old['levels_completed'] or obs['state']=='WIN')
        reset=action==0 or obs['state'] in ('NOT_PLAYED','GAME_OVER')
        if progress:
            self.hypotheses=[];self.rows={};self.edit_rows=[];self.select_rows=[];self.anchor=None;self.current=None;self.between=[];self.counts=Counter()
        scenes=self.scene(obs) if obs['state']=='NOT_FINISHED' else []
        if prior is not None:
            same=next((s for s in scenes if s['box']==prior['box'] and s['source_box']==prior['source_box']),None)
        else:same=None
        discoveries=[]
        for previous_scene in old_scenes:
            current_scene=next((q for q in scenes if q['box']==previous_scene['box'] and q['source_box']==previous_scene['source_box']),None)
            if current_scene is not None and len(current_scene['classes'])==len(previous_scene['classes']):
                changed=sum(a!=b for a,b in zip(previous_scene['classes'],current_scene['classes']))
                if changed==1:discoveries.append((previous_scene,current_scene))
        if discoveries and not progress and not reset:
            selected=min(discoveries,key=lambda pair:pair[0]['box'])
            if prior is None or prior['box']!=selected[0]['box']:self.anchor=None;self.current=None;self.between=[]
            prior,same=selected
        self.scenes=scenes
        if old is not None and action is not None:self.counts[action]+=1
        if old is not None and prior is not None and same is not None and not progress and not reset and old['state']==obs['state']=='NOT_FINISHED':
            proof=digest(dict(before=old,after=obs,action=action));self.rows[proof]=dict(before=old,after=obs,action=action)
            changed=[i for i,(a,b) in enumerate(zip(prior['classes'],same['classes'])) if a!=b]
            if len(changed)==1:
                i=changed[0];self.edit_rows.append(dict(action=action,index=i,before=prior['classes'][i],after=same['classes'][i],evidence=proof,box=prior['box']))
                if self.anchor is not None and len(self.between)==1:
                    selector,h=self.between[0]
                    self.select_rows.append(dict(action=selector,before=self.anchor,after=i,n=len(same['classes']),evidence=[h,proof],box=prior['box']))
                self.anchor=i;self.current=i;self.between=[]
            elif not changed:
                self.between.append((action,proof));model=self.select_model(action,len(same['classes']),prior['box'])
                self.current=(self.current+model['delta'])%len(same['classes']) if model and self.current is not None else None
            else:self.anchor=None;self.current=None;self.between=[]
            if intent and intent['action']==action:
                self.outcomes.append(dict(intent=intent,actual=proof,progress=False,mismatches=sum(a!=b for a,b in zip(same['classes'],same['expected']))))
        if progress or reset:self.anchor=None;self.current=None;self.between=[]
        # Prefer a panel with actual edit evidence; the direction remains a hypothesis.
        if scenes:
            self.snapshot=min(scenes,key=lambda s:(-sum(r['box']==s['box'] for r in self.edit_rows),s['box'],s['source_box']))
        else:self.snapshot=None
        self.previous=copy.deepcopy(obs)
    def select_model(self,action,n,box):
        rows=[r for r in self.select_rows if r['action']==action and r['n']==n and r['box']==box]
        deltas={(r['after']-r['before'])%n for r in rows}
        if len({r['before'] for r in rows})<2 or len(deltas)!=1 or next(iter(deltas))==0:return None
        return dict(delta=next(iter(deltas)),support=sorted({h for r in rows for h in r['evidence']}))
    def effect(self,action,shape,index,box):
        rows=[r for r in self.edit_rows if r['action']==action and r['before']==shape and r['box']==box]
        local=[r for r in rows if r['index']==index]
        if local:rows=local
        elif len({r['index'] for r in rows})<2:return None
        outcomes={r['after'] for r in rows}
        if len(outcomes)!=1:return None
        return dict(after=next(iter(outcomes)),support=sorted({r['evidence'] for r in rows}),context='selected index' if local else 'consistent transfer across indices')
    def propose(self,obs):
        if obs['state']!='NOT_FINISHED' or self.snapshot is None:return None
        legal=sorted(set(obs['available_actions'])&{1,2,3,4,5,7});s=self.snapshot;n=len(s['classes']);box=s['box']
        if not legal:return None
        wrong=[i for i,(a,b) in enumerate(zip(s['classes'],s['expected'])) if a!=b]
        if not wrong:return None
        edit_counts=Counter(r['action'] for r in self.edit_rows if r['box']==box and r['action'] in legal)
        editor=min(edit_counts,key=lambda a:(-edit_counts[a],a)) if edit_counts else None
        def result(a,kind,**extra):return dict(action=a,kind=kind,box=box,source_box=s['source_box'],expected=s['expected'],current_classes=s['classes'],selected_index=self.current,
            context=digest(obs),goal_hypothesis=s['proposal'],scope='Tentative orientation-invariant symbolic correspondence and action-model experiment; actual feedback determines progress.',**extra)
        if editor is None:return result(min(legal,key=lambda a:(self.counts[a],a)),'discover_edit')
        if self.current is None:return result(editor,'locate_edit_index')
        if self.current in wrong:
            queue=deque([(s['classes'][self.current],[])]);seen={s['classes'][self.current]}
            while queue and len(seen)<=64:
                shape,path=queue.popleft()
                if shape==s['expected'][self.current] and path:return result(path[0]['action'],'edit_plan',path=path)
                if len(path)>=12:continue
                for a in legal:
                    model=self.effect(a,shape,self.current,box)
                    if model and model['after'] not in seen:
                        seen.add(model['after']);queue.append((model['after'],path+[dict(action=a,**model)]))
            return result(editor,'discover_edit_cycle')
        queue=deque([(self.current,[])]);seen={self.current}
        while queue:
            index,path=queue.popleft()
            if index in wrong and path:return result(path[0]['action'],'select_plan',path=path)
            for a in legal:
                model=self.select_model(a,n,box)
                if model:
                    j=(index+model['delta'])%n
                    if j not in seen:seen.add(j);queue.append((j,path+[dict(action=a,**model)]))
        unknown=[a for a in legal if a not in edit_counts]
        return result(min(unknown or legal,key=lambda a:(self.counts[a],a)),'discover_selection')
    def commit(self,cert):self.pending=copy.deepcopy(cert)
    def choose(self,obs):
        if obs['state']=='WIN':return None
        if obs['state'] in ('GAME_OVER','NOT_PLAYED'):return 0
        cert=self.propose(obs)
        if cert:self.commit(cert);return cert['action']
        legal=sorted(set(obs['available_actions'])&{1,2,3,4,5,7})
        return min(legal,key=lambda a:(self.counts[a],a)) if legal else 0
