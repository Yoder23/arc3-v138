"""Keep discovery's control click outside the candidate input word."""
from refuted_tool_word_learner import Learner as Base
from literal_word_rows import center, contains, values


class Learner(Base):
    def propose(self, raw):
        c=super().propose(raw)
        if not c or c['phase']!='select':
            return c
        target=c['target']
        point=c['data']['x'],c['data']['y']
        if not any(contains(box,point) for box in target):
            return c
        # Intersecting row/column hypotheses may share cells. They can remain
        # in memory, but selecting one of those cells is not an outside control.
        assert not c.get('goal') and not c.get('evidence')
        points={center(box) for row in self.rows if row!=target and values(raw['frame'],row) is not None
            for box in row if not any(contains(t,center(box)) for t in target)}
        if not points:
            return None
        point=min(points,key=lambda p:(self.pair_trials[target,p],p))
        return dict(c,data=dict(x=point[0],y=point[1]))
