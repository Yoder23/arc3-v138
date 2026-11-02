import copy
from decorated_peg_carrier_v1 import motif
from peg_world_memory_v12 import Memory as Base
class Memory(Base):
    def __init__(self):super().__init__();self.permanent_rules=[];self.pivot_tiles={};self.movable_pivot_rules=[]
    @classmethod
    def transfer(cls,prior,rule):
        m=cls();m.__dict__.update(copy.deepcopy(prior.__dict__));m.permanent_rules=[copy.deepcopy(rule)];m.pivot_tiles={};return m
    def observe(self,raw,source):
        rules=copy.deepcopy(self.permanent_rules);oldlevel=self.level;oldtiles=self.pivot_tiles;oldposes=self.last_positions;movable=copy.deepcopy(self.movable_pivot_rules)
        v=super().observe(raw,source);self.permanent_rules=rules;self.movable_pivot_rules=movable
        if not v:return v
        if oldlevel==self.level:self.pivot_tiles=oldtiles
        for p in oldposes:
            if p not in set(map(tuple,v['layout']['scene']['cells'])):self.pivot_tiles.pop(p,None)
        f=raw['frame'];s=v['layout']['scene'];size=s['size'];pitch=s['pitch'];camera=self.camera;k=(size-1)//2
        poses=v['positions'];oy=(poses[0][0]-camera[0])%pitch;ox=(poses[0][1]-camera[1])%pitch
        for rule in self.permanent_rules:
            if rule['size']!=size:continue
            for y in range(oy,65-size,pitch):
                for x in range(ox,65-size,pitch):
                    if y<1 or x<1 or y+size>=64 or x+size>=64:continue
                    patch=tuple(tuple(f[yy][xx]for xx in range(x-1,x+size+1))for yy in range(y-1,y+size+1))
                    if not motif(f,y,x,rule):continue
                    p=(y+camera[0],x+camera[1]);self.pivot_tiles[p]=dict(position=p,local=(y,x),camera=camera,source=source,rule_source=rule['source'],pattern='retained_token_core')
        v['layout']['pivots']=sorted(self.pivot_tiles);self.layout=v['layout'];return v
    def certificate(self):return dict(super().certificate(),movable_pivot_rules=copy.deepcopy(self.movable_pivot_rules),permanent_rules=copy.deepcopy(self.permanent_rules),pivot_tiles=copy.deepcopy(list(self.pivot_tiles.values())))
