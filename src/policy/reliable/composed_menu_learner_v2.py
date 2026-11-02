"""Keep query history while planning against the latest visible query at each slot."""
from composed_menu_learner import Learner as Base
from composed_word_layouts import layouts,signature

def slot(layout,query):
    return signature(layout),tuple(query['source_box']),tuple(query['target_box'])

def content(query):
    return query['source'],query['target']

class Learner(Base):
    def __init__(self):
        super().__init__();self.latest_queries={};self.query_revisions=0

    def scene(self,obs):
        for layout in self.parsed:
            for q in layout['queries']:self.latest_queries[slot(layout,q)]=content(q)
        return [s for s in super().scene(obs)
                if self.latest_queries.get(slot(s['layout'],s['proposal']['query']))==content(s['proposal']['query'])]

    def observe(self,obs,action=None):
        progress=self.previous is not None and (
            obs['levels_completed']!=self.previous['levels_completed'] or obs['state']=='WIN')
        if progress:self.latest_queries={}
        changed=False
        if obs['state']=='NOT_FINISHED':
            for layout in layouts(obs):
                if layout.get('kind')!='composed_editable_word_layout':continue
                for q in layout['queries']:
                    old=self.latest_queries.get(slot(layout,q))
                    changed|=old is not None and old!=content(q)
        if changed:
            self.query_revisions+=1;self.choice=None;self.failed_goals.clear();self.program_cache={}
            # The action's control outcome remains evidence. A different question
            # cannot refute the candidate answering the previous question.
            if self.pending:self.pending=dict(self.pending,program_mode=False)
        super().observe(obs,action)
