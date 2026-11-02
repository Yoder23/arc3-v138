"""Temporarily defer cargo already following an observed transport entry."""
import copy
from carry_transport_learner_v9 import Controller as Base

class Controller(Base):
    def inflight(self):
        if self.held is not None or not self.transport_active():return []
        entries=self.transport.entries(self.level)
        return [copy.deepcopy(p) for _,p in sorted(self.transport.paths.items()) if p['level']==self.level
            and tuple(p['start']) in entries and len(p['steps'])>=2 and len(p['far_steps'])>=2
            and any(t['level']==self.level and tuple(t['start'])==tuple(p['start']) and t['last']<p['first'] for t in self.transport.transports)]
    def slots(self):
        # This temporary exclusion applies only while choosing loose cargo.
        # A stopped track disappears on the next actual observation, making
        # the object eligible again. It is never counted as a completed goal.
        return super().slots()|{tuple(p['last']) for p in self.inflight()}
    def answer(self,raw,v,action,tag):
        tracks=self.inflight();response=super().answer(raw,v,action,tag)
        if tracks:response['certificate']['deferred_motion']=dict(tracks=tracks,hypothesis='observe_unfinished_motion_from_a_previously_witnessed_delivery_entry')
        return response
