"""Retain query evidence and condition no-op exploration on the observed selection."""
from collections import defaultdict,deque
from atomic_program_noop_learner import Learner as Base
from atomic_program_learner import values
from atomic_word_programs import layouts,signature
from panel_hypotheses_v2 import digest

class Learner(Base):
    def __init__(self):
        super().__init__();self.indexed_noops=defaultdict(list)

    def observe(self,obs,action=None):
        old=self.previous;prior=self.snapshot;selected=self.current
        progress=old is not None and obs['levels_completed']!=old['levels_completed']
        if progress:self.indexed_noops.clear()
        same_episode=old is not None and not progress and action not in (None,0) and old['state']==obs['state']=='NOT_FINISHED'
        # A previously observed query remains available after erasure. A later
        # widget edit supplies actual role evidence; erasure itself does not.
        if same_episode and not self.active:
            parsed=layouts(obs)
            for a in self.prior_layouts:
                if not any(key[0]==signature(a) for key in self.query_memory):continue
                for b in parsed:
                    if signature(a)!=signature(b) or [p['box'] for p in a['panels']]!=[p['box'] for p in b['panels']]:continue
                    av,bv=values(a),values(b)
                    aq={(q['source'],q['target']) for q in a['queries']}
                    bq={(q['source'],q['target']) for q in b['queries']}
                    if len(av)==len(bv) and sum(x!=y for x,y in zip(av,bv))==1 and aq==bq:
                        self.active=True
                        h=digest(dict(before=old,after=obs,action=action))
                        if h not in self.role_evidence:self.role_evidence.append(h)
        super().observe(obs,action)
        if same_episode and prior is not None and selected is not None:
            if any(s['box']==prior['box'] and s['classes']==prior['classes'] for s in self.scenes):
                key=(prior['box'],prior['classes'],action,selected)
                self.indexed_noops[key].append(digest(dict(before=old,after=obs,action=action)))

    def propose(self,obs):
        c=super().propose(obs)
        if not c or c['kind']!='discover_edit_cycle' or c['selected_index'] is None:return c
        box,values,index=c['box'],c['current_classes'],c['selected_index'];n=len(values)
        legal=sorted(set(obs['available_actions'])&{1,2,3,4,5,7})
        editors={r['action'] for r in self.edit_rows if r['box']==box}
        queue=deque([(values[index],[])]);seen={values[index]};frontiers=[]
        while queue and len(seen)<=64:
            value,path=queue.popleft();state=list(values);state[index]=value;state=tuple(state)
            for action in legal:
                if self.select_model(action,n,box) is not None:continue
                if action in editors and self.indexed_noops.get((box,state,action,index)):continue
                model=self.effect(action,value,index,box)
                if model is None:frontiers.append((int(action not in editors),len(path),self.counts[action],action,value,path))
                elif len(path)<12 and model['after'] not in seen:
                    seen.add(model['after']);queue.append((model['after'],path+[dict(action=action,**model)]))
        if not frontiers:return c
        _,_,_,probe,value,path=min(frontiers,key=lambda q:q[:5])
        clean={k:v for k,v in c.items() if k not in ('noop_avoided_action','noop_support','exploration_reason')}
        return dict(clean,action=path[0]['action'] if path else probe,
            exploration_path=path,frontier_action=probe,frontier_class=value,
            exploration_scope='Follow measured edits to an unmeasured context. No-op exclusions require an actually known selected index; goal sufficiency remains a hypothesis.')
