"""Palette-independent piece identity and exact marker-pair assembly hypotheses."""
from collections import Counter
from functools import lru_cache
import numpy as np
from scipy import ndimage
from composite_connector_learner_v5 import objects,rotate
from connector_marker_parts_v1 import patches

def initial(frame):
    out=[]
    for obj in objects(frame):
        counts=Counter(c for y,x,c in obj['shape']);minor=[c for c in counts if c!=obj['body']]
        if len(minor)!=1:continue
        color=minor[0];ps=patches(obj['shape'],color)
        if not ps or len({len(p[2]) for p in ps})!=1 or min(len(p[2]) for p in ps)<4:continue
        shape=tuple((y,x,1 if c==obj['body'] else 2) for y,x,c in obj['shape']);out.append(dict(shape=shape,origin=obj['origin'],body_color=obj['body'],marker_color=color))
    return out

def locate(frame,templates):
    f=np.asarray(frame);bg=Counter(f.ravel()).most_common(1)[0][0];components=[]
    for color in sorted(set(f.ravel())-{bg}):
        labs,_=ndimage.label(f==color)
        for i,box in enumerate(ndimage.find_objects(labs)):
            if box is None or box[0].start==0 or box[1].start==0 or box[0].stop==64 or box[1].stop==64:continue
            cells=set(map(tuple,np.argwhere(labs[box]==i+1).tolist()));components.append((int(color),(box[0].start,box[1].start),cells))
    found=[]
    for template in templates:
        matches={}
        for turn in range(4):
            shape=rotate(template['shape'],turn);body={(y,x) for y,x,c in shape if c==1};y0=min(y for y,x in body);x0=min(x for y,x in body);normalized={(y-y0,x-x0) for y,x in body}
            for color,origin,cells in components:
                if cells!=normalized:continue
                origin=origin[0]-y0,origin[1]-x0
                marker_values=[f[y+origin[0],x+origin[1]] for y,x,c in shape if c==2 and 0<=y+origin[0]<64 and 0<=x+origin[1]<64]
                if len(marker_values)!=sum(c==2 for y,x,c in shape) or any(v==bg or v==color for v in marker_values):continue
                key=shape,origin;matches[key]=dict(shape=shape,origin=origin,body_color=color,marker_color=template['marker_color'])
        found.append(next(iter(matches.values())) if len(matches)==1 else None)
    return found

def absolute(obj):return {(y+obj['origin'][0],x+obj['origin'][1]):c for y,x,c in obj['shape']}
def marker_sets(obj):return [frozenset((y+obj['origin'][0],x+obj['origin'][1]) for y,x in cells) for norm,origin,cells in patches(obj['shape'],2)]
def valid(placed):
    occupied={};markers=Counter()
    for obj in placed:
        for pos,color in absolute(obj).items():
            if not(0<pos[0]<63 and 0<pos[1]<63):return False
            prior=occupied.get(pos,[])
            if prior and (color!=2 or prior!=[2]):return False
            occupied.setdefault(pos,[]).append(color)
        markers.update(marker_sets(obj))
    if any(n>2 for n in markers.values()):return False
    # Partial overlaps are forbidden even if marker colors match.
    singles=list(markers)
    return all(not a&b or a==b for i,a in enumerate(singles) for b in singles[i+1:])
def complete(placed):return valid(placed) and all(n==2 for n in Counter(p for o in placed for p in marker_sets(o)).values())

def solve(pieces,limit=12000):
    if len(pieces)>7:return None,dict(nodes=0,reason='piece_limit')
    anchor=max(range(len(pieces)),key=lambda i:len(pieces[i]['shape']));nodes=0;solutions=[];seen=set()
    def search(placed):
        nonlocal nodes
        nodes+=1
        if nodes>limit or len(solutions)>=48:return
        key=tuple(sorted((i,o['shape'],o['origin']) for i,o in placed.items()))
        if key in seen:return
        seen.add(key)
        if len(placed)==len(pieces):
            if complete(list(placed.values())):solutions.append(placed.copy())
            return
        counts=Counter(p for o in placed.values() for p in marker_sets(o));opens=[p for p,n in counts.items() if n==1]
        if not opens:return
        alternatives=[]
        for slot in opens:
            sy=min(y for y,x in slot);sx=min(x for y,x in slot);signature={(y-sy,x-sx) for y,x in slot};choices=[];dedup=set()
            for i,piece in enumerate(pieces):
                if i in placed:continue
                for turn in range(4):
                    shape=rotate(piece['shape'],turn)
                    for norm,offset,cells in patches(shape,2):
                        if set(norm)!=signature:continue
                        origin=sy-offset[0],sx-offset[1];k=i,shape,origin
                        if k in dedup:continue
                        dedup.add(k);candidate=dict(piece,shape=shape,origin=origin)
                        if valid(list(placed.values())+[candidate]):choices.append((i,candidate))
            alternatives.append(choices)
        for i,obj in min(alternatives,key=len):
            placed[i]=obj;search(placed);del placed[i]
    search({anchor:pieces[anchor]})
    def cost(solution):return sum(abs(o['origin'][0]-pieces[i]['origin'][0])+abs(o['origin'][1]-pieces[i]['origin'][1])+6*(o['shape']!=pieces[i]['shape']) for i,o in solution.items())
    best=min(solutions,key=cost) if solutions else None
    return best,dict(nodes=nodes,solutions=len(solutions),anchor=anchor,goal_is_hypothesis=True)
