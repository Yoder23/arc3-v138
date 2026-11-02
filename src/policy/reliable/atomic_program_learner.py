"""Learn which panels are editable, synthesize a program, and retain query/control evidence."""
from collections import Counter
import copy
from panel_control_learner_v2 import Learner as Controller
from panel_control_learner import identity
from panel_hypotheses_v2 import digest
from atomic_word_programs import layouts,signature,proposals

def values(layout):
    return tuple((p['background'],tuple(identity(g['mask']) for g in p['symbols'])) for p in layout['panels'])
def program_key(scene):return scene['source_box'],scene['expected']

class Learner(Controller):
    def __init__(self):
        super().__init__();self.query_memory={};self.active=False;self.role_evidence=[];self.prior_layouts=[]
        self.parsed=[];self.failed_goals=Counter();self.choice=None;self.last_completed=None;self.overflow=0

    def scene(self,obs):
        scenes=[];self.overflow=0
        for layout in self.parsed:
            sig=signature(layout)
            for query in layout['queries']:
                key=(sig,query['source'],query['target'])
                self.query_memory.setdefault(key,copy.deepcopy(query))
            queries=[q for (s,x,y),q in self.query_memory.items() if s==sig]
            if self.active:
                for query in queries:
                    found,overflow=proposals(layout,query);self.overflow+=int(overflow);scenes.extend(found)
            elif queries:
                box=(min(p['box'][0] for p in layout['panels']),min(p['box'][1] for p in layout['panels']),
                    max(p['box'][2] for p in layout['panels']),max(p['box'][3] for p in layout['panels']))
                scene=dict(box=box,source_box=queries[0]['source_box'],classes=values(layout),expected=values(layout),
                    proposal=dict(kind='unselected_rule_widget_observation'))
                scenes.append(scene)
        return scenes

    def observe(self,obs,action=None):
        old=self.previous;progress=old is not None and (obs['levels_completed']!=old['levels_completed'] or obs['state']=='WIN')
        if progress:
            self.query_memory={};self.active=False;self.role_evidence=[];self.failed_goals.clear();self.choice=None;self.last_completed=None
        parsed=layouts(obs) if obs['state']=='NOT_FINISHED' else []
        if old is not None and action not in (None,0) and not progress and old['state']==obs['state']=='NOT_FINISHED':
            for a in self.prior_layouts:
                for b in parsed:
                    if signature(a)!=signature(b) or [p['box'] for p in a['panels']]!=[p['box'] for p in b['panels']]:continue
                    av,bv=values(a),values(b)
                    oldqueries={(q['source'],q['target']) for q in a['queries']}
                    newqueries={(q['source'],q['target']) for q in b['queries']}
                    if len(av)==len(bv) and sum(x!=y for x,y in zip(av,bv))==1 and oldqueries and oldqueries==newqueries:
                        self.active=True
                        h=digest(dict(before=old,after=obs,action=action))
                        if h not in self.role_evidence:self.role_evidence.append(h)
        self.parsed=parsed
        super().observe(obs,action)
        self.prior_layouts=copy.deepcopy(parsed)
        if self.active and old is not None and action not in (None,0) and not progress and obs['state']=='NOT_FINISHED':
            for scene in self.scenes:
                if scene['classes']==scene['expected']:
                    marker=(program_key(scene),scene['classes'])
                    if marker!=self.last_completed:
                        self.failed_goals[program_key(scene)]+=1;self.last_completed=marker
                        if self.choice==program_key(scene):self.choice=None
        if self.active and self.scenes:
            self.snapshot=min(self.scenes,key=lambda s:(self.failed_goals[program_key(s)],
                int(self.choice is not None and self.choice!=program_key(s)),s['source_box'],
                sum(x!=y for x,y in zip(s['classes'],s['expected'])),s['expected']))
        if action==0:self.last_completed=None

    def propose(self,obs):
        if not self.active:return None
        cert=super().propose(obs)
        return dict(cert,program_mode=True,control_unit='panel_word',role_support=list(self.role_evidence)) if cert else None

    def commit(self,cert):
        self.choice=(cert['source_box'],cert['expected']);super().commit(cert)
