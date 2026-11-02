"""Recognize one-pixel border occlusion without treating the logical tile as absent."""
def crop(frame,box,ink):
    y,x,h,w=box
    if h%3 or w%3 or not(3<=h<=12 and 3<=w<=12 and 0<=y<=64-h and 0<=x<=64-w):return None
    center=frame[y+h//2][x+w//2]
    if center==ink:return None
    for side in ('top','bottom','left','right'):
        edge=lambda a,b: a==y if side=='top' else a==y+h-1 if side=='bottom' else b==x if side=='left' else b==x+w-1
        if not all(frame[a][b]==(center if edge(a,b) or y+h//3<=a<y+2*h//3 and x+w//3<=b<x+2*w//3 else ink) for a in range(y,y+h) for b in range(x,x+w)):continue
        return dict(box=tuple(box),ink=ink,center=center,tile_body=True,edge_occlusion=side,visible_shape_is_hypothesis=True)
    return None
