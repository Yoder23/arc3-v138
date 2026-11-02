from peg_jump_inquiry_v2 import scene as fresh
from matrix_motion_learner_v6 import objects

def scene(frame,template=None):
 s=fresh(frame)
 if s or not template:return s
 size=template['size'];field=template['field'];pitch=template['pitch']
 seeds=[o['box'][:2]for o in objects(frame)if not o.get('parts')and o['ink']==field and o['box'][2:]==(size,size)and len(o['shape'])==size*size]
 if len(seeds)<6:return None
 oy,ox=seeds[0][0]%pitch,seeds[0][1]%pitch
 if not all(y%pitch==oy and x%pitch==ox for y,x in seeds):return None
 cells=[(y,x)for y in range(oy,65-size,pitch)for x in range(ox,65-size,pitch)if all(frame[y+dy][x+dx]==field for dy,dx in[(0,0),(0,size-1),(size-1,0),(size-1,size-1)])]
 return dict(cells=cells,pitch=pitch,size=size,field=field,mark=template['mark'])
