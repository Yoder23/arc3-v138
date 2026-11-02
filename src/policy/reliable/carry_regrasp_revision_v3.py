"""After a learned grip change, keep the remaining delivery approaches open."""
from carry_regrasp_revision_v2 import Controller as Base
from observed_transport_memory_v1 import add,sub

class Controller(Base):
    def answer(self,raw,v,action,tag):
        ordering=None
        skills=[s for s in self.revised_grasp_skills.values() if s['level']==self.level and 'verified_at' in s and tuple(s['new_offset'])==self.held]
        if skills and v and tag in ('carry_toward_goal_hypothesis','release') and not self.transport_active():
            at=tuple(v['body']['box'][:2]);held=add(at,self.held)
            empty=self.slots()-(self.positions(v)-{held});choices=[]
            for slot in sorted(empty):
                route=self.route(v,sub(slot,self.held),self.held)
                if route is None:continue
                # Occupying s blocks the standing position for s+grasp.
                # This is a geometric prediction, not an observed outcome.
                blocked=sorted(q for q in empty-{slot} if sub(q,self.held)==slot)
                choices.append((len(blocked),len(route),slot,route,blocked))
            if choices:
                _,_,slot,route,blocked=min(choices)
                if route:action=route[0];tag='carry_toward_goal_hypothesis'
                else:
                    aux=[a for a in raw['available_actions'] if a not in self.motions]
                    if len(aux)==1:action=aux[0];tag='release'
                ordering=dict(grasp=self.held,skill_verified_at=min(s['verified_at'] for s in skills),empty_slots=sorted(empty),selected_slot=slot,blocked_remaining_slots=blocked,hypothesis='keep_future_grasp_approaches_open')
        response=super().answer(raw,v,action,tag)
        if ordering:response['certificate']['grasp_placement_order']=ordering
        return response
