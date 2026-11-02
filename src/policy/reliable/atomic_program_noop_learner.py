"""Use actual repeated no-op edits to choose a different exploratory action."""
from collections import defaultdict
from atomic_program_learner import Learner as Base
from panel_hypotheses_v2 import digest

class Learner(Base):
    def __init__(self):
        super().__init__();self.noops=defaultdict(list)
    def observe(self,obs,action=None):
        old=self.previous;scenes=self.scenes
        if old is not None and obs['levels_completed']!=old['levels_completed']:self.noops.clear()
        super().observe(obs,action)
        if old is None or action in (None,0) or old['state']!=obs['state'] or obs['state']!='NOT_FINISHED' or old['levels_completed']!=obs['levels_completed']:return
        seen=set()
        for before in scenes:
            key=(before['box'],before['classes'],action)
            if key in seen:continue
            if any(s['box']==before['box'] and s['classes']==before['classes'] for s in self.scenes):
                self.noops[key].append(digest(dict(before=old,after=obs,action=action)));seen.add(key)
    def propose(self,obs):
        c=super().propose(obs)
        if not c or c['kind'] not in ('locate_edit_index','discover_edit_cycle'):return c
        box,values,a=c['box'],c['current_classes'],c['action']
        evidence=self.noops.get((box,values,a),[])
        if len(evidence)<2:return c
        n=len(values);legal=sorted(set(obs['available_actions'])&{1,2,3,4,5,7})
        choices=[x for x in legal if x!=a and self.select_model(x,n,box) is None]
        if not choices:return c
        alternative=min(choices,key=lambda x:(len(self.noops.get((box,values,x),[])),self.counts[x],x))
        return dict(c,action=alternative,noop_avoided_action=a,noop_support=evidence[-2:],
            exploration_reason='Two actual edits left these widgets unchanged. Probe another non-established-selector action; selected position remains uncertain.')
