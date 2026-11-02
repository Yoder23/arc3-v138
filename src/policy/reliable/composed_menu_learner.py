"""Acquire observed word menus, remember queries and test composed programs."""
from collections import Counter,deque,defaultdict
import copy
from panel_control_learner_v2 import Learner as Controller
from panel_control_learner import identity
from panel_hypotheses_v2 import digest
from composed_word_layouts import layouts,signature
from composed_menu_equations import solutions

def values(layout):
    return tuple((p['background'],tuple(identity(g['mask']) for g in p['symbols'])) for p in layout['panels'])

def region(obs,box):
    y,x,Y,X=box
    return tuple(tuple(row[x:X+1]) for row in obs['frame'][y:Y+1])

class Learner(Controller):
    def __init__(self):
        super().__init__()
        self.parsed=[];self.query_memory={};self.domain_records=defaultdict(dict)
        self.observations={};self.role_evidence=defaultdict(list);self.failed_goals=Counter()
        self.program_cache={};self.choice=None;self.active=False;self.truncated=0

    def scene(self,obs):
        result=[];h=digest(obs)
        for layout in self.parsed:
            sig=signature(layout)
            for q in layout['queries']:
                self.query_memory.setdefault((sig,q['source'],q['target']),copy.deepcopy(q))
            classes=values(layout)
            for p,(_,word) in zip(layout['panels'],classes):
                key=tuple(p['box']),p['background'],len(word)
                if word not in self.domain_records[key]:
                    self.domain_records[key][word]=h;self.observations[h]=copy.deepcopy(obs)
            for (s,_,_),q in self.query_memory.items():
                if s!=sig:continue
                self.observations.setdefault(q['observation'],copy.deepcopy(obs) if q['observation']==h else None)
                panels=layout['panels'];box=(min(p['box'][0] for p in panels),min(p['box'][1] for p in panels),
                    max(p['box'][2] for p in panels),max(p['box'][3] for p in panels))
                stages=[dict(source_background=l['source_background'],target_background=l['target_background'],
                             schema=l['schema'],rule_boxes=[(a['box'],b['box']) for a,b in l['pairs']]) for l in layout['stages']]
                cells=[dict(box=p['box'],index=None,background=p['background'],word_length=len(p['symbols'])) for p in panels]
                proof=dict(kind='composed_word_menu_observation',query=copy.deepcopy(q),stages=stages,cells=cells,
                           scope='Observed widget layout and retained query. No completed program or goal claim.')
                result.append(dict(box=box,source_box=q['source_box'],classes=classes,expected=classes,
                                   proposal=proof,layout=layout))
        return result

    def observe(self,obs,action=None):
        old=self.previous;prior=self.parsed;pending=self.pending
        progress=old is not None and (obs['levels_completed']!=old['levels_completed'] or obs['state']=='WIN')
        if progress:
            self.query_memory={};self.domain_records=defaultdict(dict);self.observations={}
            self.role_evidence=defaultdict(list);self.failed_goals.clear();self.program_cache={}
            self.choice=None;self.active=False
        parsed=[l for l in layouts(obs) if l.get('kind')=='composed_editable_word_layout'] if obs['state']=='NOT_FINISHED' else []
        if old is not None and action not in (None,0) and not progress and old['state']==obs['state']=='NOT_FINISHED':
            for a in prior:
                for b in parsed:
                    if signature(a)!=signature(b) or [p['box'] for p in a['panels']]!=[p['box'] for p in b['panels']]:continue
                    if sum(x!=y for x,y in zip(values(a),values(b)))!=1:continue
                    queries=[q for (s,x,y),q in self.query_memory.items() if s==signature(a)]
                    if not any(all(region(old,q[k])==region(obs,q[k]) for k in ('source_box','target_box')) for q in queries):continue
                    panels=a['panels'];box=(min(p['box'][0] for p in panels),min(p['box'][1] for p in panels),
                        max(p['box'][2] for p in panels),max(p['box'][3] for p in panels))
                    h=digest(dict(before=old,after=obs,action=action))
                    if h not in self.role_evidence[box]:self.role_evidence[box].append(h)
                    self.active=True
        self.parsed=parsed
        super().observe(obs,action)
        raw=list(self.scenes);self.truncated=0;goals=[]
        if pending and pending.get('program_mode') and action==pending['action'] and not progress and obs['state']=='NOT_FINISHED':
            if any(s['source_box']==pending['source_box'] and s['classes']==pending['expected'] for s in raw):
                self.failed_goals[pending['source_box'],pending['expected']]+=1
                if self.choice==(pending['source_box'],pending['expected']):self.choice=None
        if self.active:
            for scene in raw:
                if all(self.closed(scene,i) for i in range(len(scene['classes']))):goals.extend(self.programs(scene))
        if goals:
            self.scenes=goals
            def score(s):
                key=s['source_box'],s['expected']
                unavailable=sum(target[1] not in self.domain_records[(tuple(p['box']),p['background'],len(p['symbols']))]
                    for p,target in zip(s['layout']['panels'],s['expected']))
                return self.failed_goals[key],unavailable,int(self.choice is not None and self.choice!=key),sum(a!=b for a,b in zip(s['classes'],s['expected'])),key
            self.snapshot=min(goals,key=score)

    def closed(self,scene,index):
        initial=scene['classes'][index];box=scene['box']
        for action in sorted({r['action'] for r in self.edit_rows if r['box']==box}):
            value=initial;seen={value};path=[]
            for _ in range(64):
                model=self.effect(action,value,index,box)
                if not model or model['context']!='selected index':break
                path.append(dict(action=action,before=value,**model));value=model['after']
                if value==initial:return path if len(path)>1 else None
                if value in seen:break
                seen.add(value)
        return None

    def programs(self,scene):
        layout=scene['layout'];query=scene['proposal']['query'];first,second=layout['stages']
        keys=[(tuple(b['box']),b['background'],len(b['symbols'])) for a,b in first['pairs']]
        domains=tuple(tuple(sorted(self.domain_records[k])) for k in keys)
        key=signature(layout),query['source'],query['target'],domains
        if key not in self.program_cache:
            if len(self.program_cache)>=64:self.program_cache.pop(next(iter(self.program_cache)))
            self.program_cache[key]=solutions(query['source'],query['target'],first['schema'],second['schema'],domains)
        found=self.program_cache[key];self.truncated+=int(found['truncated']);out=[]
        for program in found['programs']:
            expected={}
            for stage,part in ((first,program['first']),(second,program['second'])):
                for (a,b),(left,right) in zip(stage['pairs'],part):
                    expected[tuple(a['box'])]=left;expected[tuple(b['box'])]=right
            proof=dict(scene['proposal'],kind='composed_editable_word_program',program=program,
                domain_support=[dict(box=k[0],background=k[1],word=word,observation=self.domain_records[k][word])
                                for k,(_,word) in zip(keys,program['first'])],
                scope='Tentative two-stage word equation from a retained query and actually observed intermediate word values. Actual feedback establishes goal sufficiency.')
            goal=tuple((p['background'],expected[tuple(p['box'])]) for p in layout['panels'])
            out.append(dict(scene,proposal=proof,expected=goal))
        return out

    def propose(self,obs):
        if obs['state']!='NOT_FINISHED' or self.snapshot is None:return None
        s=self.snapshot;box=s['box'];n=len(s['classes'])
        if s['proposal']['kind']=='composed_editable_word_program':
            cert=super().propose(obs)
            if cert:return dict(cert,program_mode=True,control_unit='panel_word',role_support=list(self.role_evidence.get(box,[])))
        legal=sorted(set(obs['available_actions'])&{1,2,3,4,5,7})
        if not legal:return None
        editors=Counter(r['action'] for r in self.edit_rows if r['box']==box and r['action'] in legal)
        editor=min(editors,key=lambda a:(-editors[a],a)) if editors else None
        def result(a,kind,**extra):
            proof=dict(s['proposal'])
            if proof['kind']=='composed_editable_word_program':
                proof={k:v for k,v in proof.items() if k not in ('program','domain_support')}
                proof['kind']='composed_word_menu_observation'
            return dict(action=a,kind=kind,box=box,source_box=s['source_box'],expected=s['classes'],current_classes=s['classes'],
                selected_index=self.current,context=digest(obs),goal_hypothesis=proof,program_mode=False,
                control_unit='panel_word',role_support=list(self.role_evidence.get(box,[])),
                scope='Acquire actual word transitions and selection. No solved-goal assertion.',**extra)
        if editor is None:return result(min(legal,key=lambda a:(self.counts[a],a)),'discover_edit')
        if self.current is None:return result(editor,'locate_edit_index')
        closed={i:bool(self.closed(s,i)) for i in range(n)}
        if not closed[self.current]:return result(editor,'discover_edit_cycle')
        queue=deque([(self.current,[])]);seen={self.current}
        while queue:
            index,path=queue.popleft()
            if not closed[index] and path:
                return result(path[0]['action'],'discover_selection',acquisition_path=path,acquisition_target_index=index)
            for action in legal:
                model=self.select_model(action,n,box)
                if model:
                    after=(index+model['delta'])%n
                    if after not in seen:seen.add(after);queue.append((after,path+[dict(action=action,**model)]))
        unknown=[a for a in legal if a not in editors and self.select_model(a,n,box) is None]
        def information(a):
            origins={r['before'] for r in self.select_rows if r['action']==a and r['box']==box and r['n']==n}
            return int(self.current in origins),-len(origins),self.counts[a],a
        return result(min(unknown or legal,key=information),'discover_selection')

    def commit(self,cert):
        if cert.get('program_mode'):self.choice=cert['source_box'],cert['expected']
        super().commit(cert)
