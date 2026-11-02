"""Remember raw body templates after a measured, bounded completion succeeds."""
from collections import defaultdict
import copy
from observed_body_completion import candidates,complete
from visual_transform_learner import parts,canonical,identity,digest

class Memory:
    def __init__(self):
        self.templates={};self.acquisitions=[]

    def observe(self,before,action,after,selected):
        if before is None:return
        if before['levels_completed']!=after['levels_completed'] or after['state']=='WIN':
            self.templates={};self.acquisitions=[];return
        if before['state']!=after['state'] or after['state']!='NOT_FINISHED' or not selected:return
        if selected.get('kind')!='retained_pose_alignment':return
        assert selected['action']==action and selected['context']==digest(before)
        actor=selected['actor'];key=identity(actor)
        if key in self.templates or actor not in parts(before['frame']):return
        predicted=selected['path'][0]['after']
        matched=[p for p in candidates(after,before,actor) if p['completed_pose']==predicted]
        if len(matched)!=1:return
        self.templates[key]=dict(observation=copy.deepcopy(before),pose=copy.deepcopy(actor))
        self.acquisitions.append(dict(before=digest(before),after=digest(after),action=action,proof=matched[0]))

    def unique(self,frame):
        grouped=defaultdict(list)
        for raw in parts(frame):
            key=identity(raw);pose=raw
            if key not in self.templates:
                change=complete(raw[1])
                if change:
                    shape,_=change;completed=(raw[0],shape,raw[2])
                    if identity(completed) in self.templates:pose=completed
            grouped[identity(pose)].append(pose)
        return {key:values[0] for key,values in grouped.items() if len(values)==1}

    def sources(self):
        out=[]
        for key,source in self.templates.items():
            acquired=[a for a in self.acquisitions if identity(a['proof']['source_pose'])==key]
            assert len(acquired)==1
            out.append(dict(copy.deepcopy(source),acquisition=copy.deepcopy(acquired[0])))
        return out
