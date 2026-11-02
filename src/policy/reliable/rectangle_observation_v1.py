from component_figure_model_v4 import ignore_mask

def bounds(frame,color,sc):
 mask=ignore_mask(sc);ps={(y,x) for y,row in enumerate(frame[:62]) for x,c in enumerate(row) if c==color and (y,x) not in mask}
 if len(ps)<12:return None
 a=min(y for y,x in ps);b=min(x for y,x in ps);c=max(y for y,x in ps);d=max(x for y,x in ps)
 if c-a<2 or d-b<2:return None
 edge={(y,x) for y in range(a,c+1) for x in range(b,d+1) if y in (a,c) or x in (b,d)}-mask
 if ps-edge or len(ps)<.7*len(edge):return None
 return [a,b,c,d]
