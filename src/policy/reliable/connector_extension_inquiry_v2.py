"""Continue a bounded inquiry only after two witnessed nonrigid extension effects."""
from collections import Counter
from composite_connector_learner_v5 import objects
from visual_transform_learner import digest
class ExtensionInquiry:
    def __init__(self):self.evidence=[];self.level=None;self.streak=0;self.attempts=0
    def observe(self,before,last,after):
        if self.level!=after['levels_completed']:self.level=after['levels_completed'];self.streak=0;self.attempts=0
        if before is None or not last or last[0]!=5 or before['levels_completed']!=after['levels_completed']:return False
        candidates=[]
        for a in objects(before['frame']):
            ac=Counter(c for y,x,c in a['shape'])
            if len(ac)!=3:continue
            for b in objects(after['frame']):
                bc=Counter(c for y,x,c in b['shape'])
                if a['origin']!=b['origin'] or ac.keys()!=bc.keys():continue
                grown=[c for c in ac if bc[c]>ac[c]];stable=[c for c in ac if bc[c]==ac[c]]
                if not grown or len(grown)+len(stable)!=3:continue
                moving=[c for c in stable if {(y,x) for y,x,k in a['shape'] if k==c}!={(y,x) for y,x,k in b['shape'] if k==c}]
                if len(moving)!=1:continue
                preserved=sorted(set(ac)-set(moving));left={(y,x,c) for y,x,c in a['shape'] if c in preserved};right={(y,x,c) for y,x,c in b['shape'] if c in preserved}
                if not left<right:continue
                candidates.append((a,b,preserved,moving))
        if len(candidates)!=1:self.streak=0;return False
        a,b,grown,stable=candidates[0];self.streak+=1;self.attempts+=1
        self.evidence.append(dict(source=digest(dict(before=before,action=last[0],data=last[1],after=after)),kind='observed_nonrigid_extension',old_counts=dict(Counter(c for y,x,c in a['shape'])),new_counts=dict(Counter(c for y,x,c in b['shape'])),preserved_colors=grown,moving_auxiliary=stable[0]))
        return self.streak>=2 and self.attempts<8
