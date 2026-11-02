"""Match the visible portion of an earlier observed carrier border at a frame edge."""
from matrix_motion_learner_v6 import objects
def clipped(frame,template):
    n=template['body']['box'][2];ink=template['body']['ink'];out=[]
    for o in objects(frame):
        if o.get('parts')or o['ink']!=ink:continue
        y,x,h,w=o['box']
        if h>n or w>n or h==w==n:continue
        if h<n:
            if y==0:y=-(n-h)
            elif y+h!=64:continue
        if w<n:
            if x==0:x=-(n-w)
            elif x+w!=64:continue
        visible=[(dy,dx)for dy in range(n)for dx in range(n)if(dy in(0,n-1)or dx in(0,n-1))and 0<=y+dy<64 and 0<=x+dx<64]
        actual={(o['box'][0]+dy,o['box'][1]+dx)for dy,dx in o['shape']}
        if len(visible)<n+2 or actual!={(y+dy,x+dx)for dy,dx in visible}:continue
        if all(frame[y+dy][x+dx]==ink for dy,dx in visible):out.append(dict(ink=ink,box=(y,x,n,n),shape=visible,clipped_template_source=template['source'],hypothesis='visible_subset_of_retained_full_carrier_border'))
    return sorted(out,key=lambda v:v['box'])
