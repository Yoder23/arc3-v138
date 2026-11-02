"""Learn a jump relation from a highlighted click outcome, then search its consequences."""
from collections import Counter
import copy
from matrix_motion_learner_v6 import objects

def scene(frame):
 solid=[o for o in objects(frame) if not o.get('parts') and o['box'][2]==o['box'][3] and 2<=o['box'][2]<=8 and len(o['shape'])==o['box'][2]**2]
 groups=Counter((o['ink'],o['box'][2]) for o in solid)
 if not groups:return None
 (field,size),n=groups.most_common(1)[0]
 if n<6:return None
 seeds=[o['box'][:2] for o in solid if o['ink']==field and o['box'][2]==size]
 diffs=[abs(a[1]-b[1]) for a in seeds for b in seeds if a[0]==b[0] and size<abs(a[1]-b[1])<=size*3]
 if not diffs:return None
 pitch=min(diffs);oy=min(y for y,x in seeds)%pitch;ox=min(x for y,x in seeds)%pitch;cells=[]
 for y in range(oy,65-size,pitch):
  for x in range(ox,65-size,pitch):
   if all(frame[y+dy][x+dx]==field for dy,dx in ((0,0),(0,size-1),(size-1,0),(size-1,size-1))):cells.append((y,x))
 cores=Counter(frame[y+(size-1)//2][x+(size-1)//2] for y,x in cells if frame[y+(size-1)//2][x+(size-1)//2]!=field)
 if not cores:return None
 mark=cores.most_common(1)[0][0]
 return dict(cells=cells,pitch=pitch,size=size,field=field,mark=mark)
def pegs(frame,s):
 k=(s['size']-1)//2;return tuple(i for i,(y,x) in enumerate(s['cells']) if frame[y+k][x+k]==s['mark'])
def plans(s,present,forbidden=(),limit=250000):
 cells=list(map(tuple,s['cells']));index={p:i for i,p in enumerate(cells)};moves=[];pitch=s['pitch']
 for a,(y,x) in enumerate(cells):
  for dy,dx in ((pitch,0),(-pitch,0),(0,pitch),(0,-pitch)):
   if (y+dy,x+dx) in index and (y+2*dy,x+2*dx) in index:moves.append((a,index[y+dy,x+dx],index[y+2*dy,x+2*dx]))
 start=sum(1<<i for i in present);dead=set();count=0
 def visit(state):
  nonlocal count
  count+=1
  if count>limit:return None
  if state.bit_count()==1:return []
  if state in dead:return None
  options=[]
  for a,b,c in moves:
   if state>>a&1 and state>>b&1 and not state>>c&1 and (state,a,b,c) not in forbidden:
    nxt=state^(1<<a)^(1<<b)^(1<<c);degree=sum(bool(nxt>>v&1)+bool(nxt>>u&1) for u,v,z in moves if z==c);options.append((-degree,a,b,c,nxt))
  for _,a,b,c,nxt in sorted(options):
   rest=visit(nxt)
   if rest is not None:return [(a,b,c)]+rest
  dead.add(state);return None
 result=visit(start);return result,count
class Agent:
 def __init__(self,prior=None):self.prior=prior;self.active=True;self.t=0;self.level=None;self.s=None;self.previous=None;self.selected=None;self.pending=None;self.rule_memory=[];self.progress_memory=[];self.failures=[];self.forbidden=set();self.probed=set()
 def point(self,i):y,x=self.s['cells'][i];k=(self.s['size']-1)//2;return dict(x=x+k,y=y+k)
 def answer(self,raw,i,tag,extra=None):
  c=dict(kind='peg_jump_inquiry',source=self.t,scene=copy.deepcopy(self.s),pegs=pegs(raw['frame'],self.s),rule_memory=copy.deepcopy(self.rule_memory),progress_memory=copy.deepcopy(self.progress_memory),failures=copy.deepcopy(self.failures),tag=tag,goal_is_hypothesis=True,**(extra or {}));d=self.point(i);self.previous=dict(raw=copy.deepcopy(raw),data=d,certificate=copy.deepcopy(c),source=self.t);self.t+=1;return dict(done=False,action=6,data=d,certificate=c)
 def respond(self,raw):
  old=self.previous
  if self.level!=raw['levels_completed']:
   if old and self.level is not None:self.progress_memory.append(dict(source=old['source'],from_level=self.level,to_level=raw['levels_completed'],goal='one_remaining_mark_hypothesis'))
   self.s=scene(raw['frame']);self.level=raw['levels_completed'];self.selected=None;self.pending=None;self.forbidden=set();self.probed=set()
   if self.s:self.s['source']=self.t
  if raw['state']!='NOT_FINISHED' or not self.s:return dict(done=True,action=None,data={})
  occupied=pegs(raw['frame'],self.s)
  if self.pending and old:
   p=self.pending;before=tuple(p['pegs']);removed=sorted(set(before)-set(occupied));added=sorted(set(occupied)-set(before))
   if len(removed)==2 and len(added)==1 and p['source_index'] in removed:
    a=p['source_index'];b=next(i for i in removed if i!=a);c=added[0];A,B,C=[self.s['cells'][i]for i in (a,b,c)]
    if all(2*B[k]==A[k]+C[k]for k in (0,1)) and sum(abs(A[k]-B[k])for k in (0,1))==self.s['pitch']:self.rule_memory.append(dict(source=old['source'],selection_source=p['selection_source'],scene=copy.deepcopy(self.s),before=before,after=occupied,move=(a,b,c),hypothesis='jump_over_one_mark_to_empty_cell_removes_source_and_middle'))
   else:
    self.failures.append(dict(source=old['source'],before=before,after=occupied,attempt=p))
    if 'move' in p:self.forbidden.add((sum(1<<i for i in before),*p['move']))
   self.pending=None;self.selected=None
  if self.selected is not None:
   selected=self.selected;source=old['source'];before=old['raw']['frame'];now=raw['frame'];k=(self.s['size']-1)//2
   highlights=[i for i,(y,x)in enumerate(self.s['cells'])if i not in occupied and all(before[y+dy][x+dx]==self.s['field'] for dy in range(self.s['size']) for dx in range(self.s['size'])) and any(now[y+dy][x+dx] not in (self.s['field'],self.s['mark']) for dy in range(self.s['size']) for dx in range(self.s['size']))]
   if highlights:
    target=self.selected_target if hasattr(self,'selected_target') and self.selected_target in highlights else highlights[0];p=dict(pegs=occupied,source_index=selected,selection_source=source)
    if hasattr(self,'selected_move') and self.selected_move and target==self.selected_move[2]:p['move']=self.selected_move
    self.pending=p;return self.answer(raw,target,'test_observed_landing',dict(selection_source=source,highlight=target,planned_move=p.get('move')))
   self.probed.add(selected);self.selected=None
  if self.rule_memory:
   plan,n=plans(self.s,occupied,self.forbidden)
   if plan:
    a,b,c=plan[0];self.selected=a;self.selected_target=c;self.selected_move=(a,b,c);return self.answer(raw,a,'select_planned_jump',dict(plan=plan,search_nodes=n,rule_source=self.rule_memory[0]['source']))
  choices=[i for i in occupied if i not in self.probed]
  if not choices:return dict(done=True,action=None,data={})
  self.selected=choices[0];self.selected_move=None;return self.answer(raw,self.selected,'inquire_mark')
