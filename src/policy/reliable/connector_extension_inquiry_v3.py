"""Recognize insertion/stretching when preserved subregions translate together."""
from collections import Counter
from connector_extension_inquiry_v2 import ExtensionInquiry as Prior
from composite_connector_learner_v5 import objects
from visual_transform_learner import digest
class ExtensionInquiry(Prior):
    def __init__(self):super().__init__();self.partition_level=None;self.partition_streak=0;self.partition_attempts=0;self.partition_axis=None
    def observe(self,before,last,after):
        if self.partition_level!=after['levels_completed']:self.partition_level=after['levels_completed'];self.partition_streak=0;self.partition_attempts=0;self.partition_axis=None
        old=len(self.evidence);result=super().observe(before,last,after)
        if len(self.evidence)>old:return result
        if before is None or not last or last[0]!=5 or before['levels_completed']!=after['levels_completed']:return False
        candidates=[]
        for a in objects(before['frame']):
            ac=Counter(c for y,x,c in a['shape'])
            if len(ac)!=3:continue
            for b in objects(after['frame']):
                bc=Counter(c for y,x,c in b['shape'])
                if a['origin']!=b['origin'] or ac.keys()!=bc.keys():continue
                grown=[c for c in ac if bc[c]>ac[c]]
                if len(grown)!=1 or any(bc[c]!=ac[c] for c in ac if c not in grown):continue
                sizea=tuple(1+max(q[k] for q in a['shape']) for k in (0,1));sizeb=tuple(1+max(q[k] for q in b['shape']) for k in (0,1));axes=[k for k in (0,1) if sizeb[k]>sizea[k]]
                if len(axes)!=1:continue
                axis=axes[0];step=sizeb[axis]-sizea[axis]
                if sizeb[1-axis]!=sizea[1-axis]:continue
                target={(y,x):c for y,x,c in b['shape']};cuts=[]
                for cut in range(1,sizea[axis]):
                    mapped={tuple(q[k]+(step if k==axis and q[axis]>=cut else 0) for k in (0,1)):q[2] for q in a['shape']}
                    if not all(target.get(p)==c for p,c in mapped.items()):continue
                    extra=set(target)-set(mapped)
                    if extra and all(target[p]==grown[0] and cut<=p[axis]<cut+step for p in extra):cuts.append(cut)
                if cuts:candidates.append((a,b,axis,step,cuts,grown[0]))
        if len(candidates)!=1:self.partition_streak=0;return False
        a,b,axis,step,cuts,color=candidates[0];self.partition_streak=self.partition_streak+1 if self.partition_axis==axis else 1;self.partition_axis=axis;self.partition_attempts+=1
        self.evidence.append(dict(source=digest(dict(before=before,action=last[0],data=last[1],after=after)),kind='observed_partition_extension',before=a,after=b,axis=axis,step=step,cuts=cuts,inserted_color=color))
        return self.partition_streak>=2 and self.partition_attempts<8
