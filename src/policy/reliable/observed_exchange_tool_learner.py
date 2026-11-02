"""Learn a tentative two-endpoint exchange relation and verify selection feedback."""
from collections import Counter
import copy
from appearance_disjoint_tool_learner import Learner as Base
from literal_word_rows import values,center,contains
from visual_transform_learner import public

def local_change(a,b,p,radius=3):
    x,y=p
    return sum(a[v][u]!=b[v][u] for v in range(max(0,y-radius),min(len(a),y+radius+1))
        for u in range(max(0,x-radius),min(len(a[0]),x+radius+1)))

class Learner(Base):
    def __init__(self,*,retain=True):
        super().__init__(retain=retain)
        self.exchanges=[];self.selection_failures=Counter();self.exchange_failures=Counter()

    def observe(self,raw,action=None,data=None):
        old,pending=self.previous,self.pending
        obs=public(raw)
        super().observe(obs,action,data)
        same=old is not None and old['state']==obs['state']=='NOT_FINISHED' and old['levels_completed']==obs['levels_completed']
        if same and pending and pending.get('exchange_evidence'):
            p=pending['exchange_context'];target=p['target'];control=p['source_point']
            if pending['phase']=='select':
                quiet=(values(old['frame'],target)==values(obs['frame'],target)
                    and old['frame'][control[1]][control[0]]==obs['frame'][control[1]][control[0]])
                cue=local_change(old['frame'],obs['frame'],control)
                if not quiet or not cue:
                    self.queued=None
                    if quiet and not cue:self.selection_failures[tuple(control),p['source_color']]+=1
            elif pending['phase']=='apply':
                after=values(obs['frame'],target)
                ok=(after is not None and after[p['token']]==p['source_color']
                    and obs['frame'][control[1]][control[0]]==p['target_color'])
                if not ok:self.exchange_failures[tuple(control),p['source_color'],center(target[p['token']]),p['target_color']]+=1
        if not same or action!=6 or len(self.history)<2:return
        select,apply=self.history[-2:]
        if select['action']!=6 or select['after']!=apply['before']:return
        a,b,c=select['before'],apply['before'],apply['after']
        if a['state']!=b['state'] or a['levels_completed']!=b['levels_completed']:return
        source=select['data']['x'],select['data']['y'];point=data['x'],data['y']
        color=a['frame'][source[1]][source[0]]
        if color!=b['frame'][source[1]][source[0]] or not local_change(a['frame'],b['frame'],source):return
        for target in self.rows:
            hits=[i for i,box in enumerate(target) if contains(box,point)]
            if len(hits)!=1:continue
            k=hits[0];left=values(b['frame'],target);right=values(c['frame'],target)
            if left is None or right is None or values(a['frame'],target)!=left:continue
            if left[k]==color or right[k]!=color or c['frame'][source[1]][source[0]]!=left[k]:continue
            expected=list(left);expected[k]=color
            for i,box in enumerate(target):
                if contains(box,source):expected[i]=left[k]
            if tuple(expected)!=right:continue
            self.exchanges.append(dict(select_index=len(self.history)-2,apply_index=len(self.history)-1,
                target=target,token=k,source_point=source,source_color=color,target_color=left[k]))

    def propose(self,raw):
        obs=public(raw);c=super().propose(obs)
        if not c:return c
        if c['phase']=='apply':
            if self.queued and self.queued.get('exchange_evidence'):
                c['exchange_evidence']=copy.deepcopy(self.queued['exchange_evidence'])
                c['exchange_context']=copy.deepcopy(self.queued['exchange_context'])
            return c
        if c['phase']!='select' or not c.get('goal') or not self.exchanges:return c
        target=c['goal']['target'];current=values(obs['frame'],target)
        mismatch=[i for i,(a,b) in enumerate(zip(current,c['goal']['word'])) if a!=b]
        if not mismatch:return c
        k=mismatch[0];desired=c['goal']['word'][k];point=center(target[k]);options=[]
        for row in self.rows:
            if values(obs['frame'],row) is None:continue
            for box in row:
                source=center(box)
                if contains(target[k],source) or obs['frame'][source[1]][source[0]]!=desired:continue
                if self.selection_failures[source,desired]:continue
                disturb=any(contains(t,source) and current[i]==c['goal']['word'][i] for i,t in enumerate(target))
                failures=self.exchange_failures[source,desired,point,current[k]]
                options.append((disturb,failures,abs(source[0]-point[0])+abs(source[1]-point[1]),source))
        if not options:return c
        _,_,_,source=min(options)
        c.update(data=dict(x=source[0],y=source[1]),followup=point,evidence=[],predicted_token=desired,
            exchange_evidence=copy.deepcopy(self.exchanges[-4:]),
            exchange_context=dict(target=target,token=k,source_point=source,source_color=desired,target_color=current[k],
                selection_cue_radius=3,scope='A previously observed exchange motivates this tentative object-transfer attempt. Require actual local selection feedback before application; measure both endpoint outcomes and retain contradictions.'))
        c.pop('conditional_context',None);c.pop('appearance_context',None)
        return c

    def commit(self,c):
        super().commit(c)
        if c['phase']=='select' and c.get('exchange_evidence'):
            self.queued['exchange_evidence']=copy.deepcopy(c['exchange_evidence'])
            self.queued['exchange_context']=copy.deepcopy(c['exchange_context'])
