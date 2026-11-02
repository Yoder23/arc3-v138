"""Prefer untested control/state pairs when no supported route reaches the goal."""
from collections import Counter
import copy
from global_correspondence_learner_v1 import Learner as Prior,Controller as BaseController
from global_correspondence_base_v1 import Learner as Broad
from segmented_track_geometry_v1 import read

class Learner(Prior):
    def propose(self,raw):
        earlier=self.established.propose(raw)
        if earlier and earlier['kind']=='track_conjunction_plan':return earlier
        broader=Broad.propose(self,raw)
        if not broader or broader['kind']!='track_control_probe':return broader or earlier
        cells=broader['scene']['cells'];current=broader['scene']['word'];contexts=Counter()
        start=0 if self.retain else 1+max((i for i,e in enumerate(self.history) if e['after']['state']=='GAME_OVER'),default=-1)
        for e in self.history[start:]:
            if e['action']!=6 or e['before']['levels_completed']!=raw['levels_completed'] or e['before']['state']!='NOT_FINISHED':continue
            before=read(e['before']['frame'],cells)
            if before is not None:contexts[((e['data'].get('x'),e['data'].get('y')),before)]+=1
        control=min(broader['scene']['controls'],key=lambda c:(contexts[c['point'],current],self.trials[cells,c['point']],c['box']))
        broader['control']=copy.deepcopy(control);broader['data']=dict(zip(('x','y'),control['point']))
        broader['inquiry']=dict(kind='new_control_context',exact_context_trials=contexts[control['point'],current])
        return broader

class Controller(BaseController):
    def __init__(self,prior=None,retain=True):
        super().__init__(prior,retain);self.learner=Learner(retain)
