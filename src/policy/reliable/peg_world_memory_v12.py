import copy
from retained_peg_scene_v1 import scene
from peg_jump_inquiry_v2 import scene as fresh_scene
from coupled_peg_model_v3 import carriers
from observed_viewport_memory_v4 import infer
from peg_carrier_templates_v1 import clipped
from decorated_peg_carrier_v1 import carriers as decorated
class Memory:
    def __init__(self):self.level=None;self.camera=(0,0);self.previous=None;self.camera_events=[];self.tiles={};self.mark_support={};self.last_positions=();self.ink=None;self.track=None;self.origin=None;self.layout=None;self.template=None;self.track_template=None;self.scene_support=None;self.scene_transfer=None
    def observe(self,raw,source):
        if raw['levels_completed']!=self.level:
            template=self.template;track_template=self.track
            self.__init__();self.template=template;self.track_template=track_template;self.level=raw['levels_completed'];self.origin=source
        f=raw['frame'];fresh=fresh_scene(f);s=fresh or scene(f,self.layout['scene']if self.layout else None)
        if not fresh and s:self.scene_transfer=copy.deepcopy(self.scene_support)
        if fresh:
            k=(s['size']-1)//2;p=next(p for p in s['cells']if f[p[0]+k][p[1]+k]==s['mark']);self.scene_support=dict(source=source,local=p,size=s['size'],pitch=s['pitch'],field=s['field'],mark=s['mark'])
        if not s:return None
        if self.previous:
            r=infer(self.previous['frame'],f,self.layout['scene']if self.layout else s,self.ink)
            if r['supported']:
                self.camera=tuple(self.camera[k]+r['delta'][k]for k in(0,1));self.camera_events.append(dict(source=self.previous['source'],level=self.level,**r))
        known=tuple((y-self.camera[0],x-self.camera[1])for y,x in self.last_positions)
        known=tuple((y,x)for y,x in known if 0<y and 0<x and y+s['size']<64 and x+s['size']<64)
        bodies=carriers(f,s['size'],self.ink,known)
        bodies+= [b for b in decorated(f,self.template,getattr(self,'permanent_rules',[]))if b['box']not in [o['box']for o in bodies]]
        bodies.sort(key=lambda b:b['box'])
        if not bodies and self.template and self.template['body']['box'][2]==s['size']+2:bodies=clipped(f,self.template)
        if not bodies:return None
        if not bodies[0].get('clipped_template_source')and not bodies[0].get('decorated_template_source')and (self.template is None or self.template['body']['ink']!=bodies[0]['ink']):self.template=dict(source=source,body=copy.deepcopy(bodies[0]))
        if self.ink is None:self.ink=bodies[0]['ink']
        if self.track is None:
            y,x=bodies[0]['box'][:2];self.track=f[y-1][x-1]if y>0 and x>0 else self.track_template
            if self.track is None:return None
        local=tuple((o['box'][0]+1,o['box'][1]+1)for o in bodies);pos=tuple((y+self.camera[0],x+self.camera[1])for y,x in local);pitch=s['pitch'];k=(s['size']-1)//2;rail=[]
        for y in range(local[0][0]%pitch,65-s['size'],pitch):
            for x in range(local[0][1]%pitch,65-s['size'],pitch):
                if (y,x)in local or all(f[y+dy][x+dx]==self.track for dy in(k,k+1)for dx in(k,k+1)):rail.append((y,x))
        for role,points in [('cell',s['cells']),('rail',rail)]:
            for p in points:
                world=(p[0]+self.camera[0],p[1]+self.camera[1]);self.tiles[role,world]=dict(role=role,position=world,local=p,camera=self.camera,source=source)
        cells={p for role,p in self.tiles if role=='cell'};rails={p for role,p in self.tiles if role=='rail'}
        for p in self.last_positions:
            if p not in cells:self.mark_support.pop(p,None)
        for p in cells|set(pos):
            y,x=p[0]-self.camera[0],p[1]-self.camera[1]
            if 0<=y<=64-s['size']and 0<=x<=64-s['size']:
                if f[y+k][x+k]==s['mark']:self.mark_support[p]=dict(position=p,local=(y,x),camera=self.camera,source=source)
                else:self.mark_support.pop(p,None)
        self.previous=dict(source=source,frame=copy.deepcopy(f));self.last_positions=pos
        L=dict(scene=dict(s,cells=sorted(cells)),rails=sorted(rails),carrier_ink=self.ink,track=self.track,initial_positions=pos)
        self.layout=L
        return dict(layout=L,positions=pos,marks=frozenset(self.mark_support),carriers=bodies,camera=self.camera)
    def certificate(self):
        result=dict(carrier_template=copy.deepcopy(self.template),origin=self.origin,level=self.level,camera=self.camera,camera_events=copy.deepcopy(self.camera_events),tiles=copy.deepcopy(list(self.tiles.values())),mark_support=copy.deepcopy(list(self.mark_support.values())))

        if self.scene_transfer:result['scene_transfer']=copy.deepcopy(self.scene_transfer)
        return result
