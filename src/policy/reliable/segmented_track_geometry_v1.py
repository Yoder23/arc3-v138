"""Tentative row,column andperimeter tracks over visible uniform tokens."""
from collections import defaultdict
from cyclic_perimeter_geometry_v1 import inventory,parse,markers

def scenes(frame):
    items=inventory(frame);groups=defaultdict(list);out=[]
    for t in items:
        y,x,h,w=t['box']
        if 2<=h==w<=5 and t['area']==h*w:groups[h].append(t)
    for size,group in groups.items():
        if not 8<=len(group)<=80:continue
        boxes=tuple(sorted(t['box'] for t in group));lookup={b:i for i,b in enumerate(boxes)}
        word=tuple(frame[y][x] for y,x,h,w in boxes)
        grid=dict(boxes=boxes,word=word,size=size)
        observed=markers(frame,grid);goals={}
        for g in observed:
            k=g['index'],g['ink']
            if k not in goals or g['marker_boxes'][0][2]>goals[k]['marker_boxes'][0][2]:goals[k]=g
        # Corner marker blocks can have the same size as movable tokens.
        # Their geometry is role evidence; never make them state variables that
        # disappear with the example at failure.
        regions=[b for g in goals.values() for b in g['marker_boxes']]
        boxes=tuple(b for b in boxes if not any(a<=b[0] and c<=b[1] and b[0]+b[2]<=a+h and b[1]+b[3]<=c+w for a,c,h,w in regions))
        if not 8<=len(boxes)<=80:continue
        lookup={b:i for i,b in enumerate(boxes)};word=tuple(frame[y][x] for y,x,h,w in boxes)
        grid=dict(boxes=boxes,word=word,size=size);goals={}
        for g in markers(frame,grid):
            k=g['index'],g['ink']
            if k not in goals or g['marker_boxes'][0][2]>goals[k]['marker_boxes'][0][2]:goals[k]=g
        tracks=set()
        for axis in (0,1):
            lines=defaultdict(list)
            for i,b in enumerate(boxes):lines[b[1-axis]].append(i)
            for indexes in lines.values():
                indexes.sort(key=lambda i:boxes[i][axis]);positions=[boxes[i][axis] for i in indexes]
                if len(indexes)>=3:
                    # A gap between independent groups does not erase each
                    # group's regular track. Maximal equal-gap runs preserve
                    # every earlier whole-row hypothesis as a special case.
                    start=0
                    for stop in range(2,len(indexes)+1):
                        boundary=stop==len(indexes) or positions[stop]-positions[stop-1]!=positions[stop-1]-positions[stop-2]
                        if boundary:
                            if stop-start>=3 and positions[start+1]-positions[start]>size:tracks.add(tuple(indexes[start:stop]))
                            start=stop-1
        for ring in parse(frame):
            if all(b in lookup for b in ring['boxes']):tracks.add(tuple(lookup[b] for b in ring['boxes']))
        if not tracks:continue
        excluded=list(boxes)+[b for g in goals.values() for b in g['marker_boxes']]
        control=[]
        for t in items:
            y,x,h,w=t['box'];point=(x+(w-1)//2,y+(h-1)//2)
            if not(2<=h<=10 and 2<=w<=10 and 4<=t['area']<=80):continue
            if any(a<=point[1]<a+c and b<=point[0]<b+d for a,b,c,d in excluded):continue
            control.append(dict(t,point=point))
        out.append(dict(cells=boxes,word=word,size=size,tracks=tuple(sorted(tracks)),
            goals=tuple(goals[k] for k in sorted(goals)),controls=tuple(sorted(control,key=lambda c:c['box']))))
    return sorted(out,key=lambda s:(-len(s['goals']),-len(s['cells']),s['cells']))

def permutations(scene):
    result={};n=len(scene['cells'])
    for track in scene['tracks']:
        for k in range(1,len(track)):
            perm=list(range(n))
            for i,dest in enumerate(track):perm[dest]=track[(i+k)%len(track)]
            result[tuple(perm)]=dict(track=track,shift=k)
    return result

def apply(word,perm):return tuple(word[i] for i in perm)
def read(frame,cells):
    values=[]
    for y,x,h,w in cells:
        v={frame[a][b] for a in range(y,y+h) for b in range(x,x+w)}
        if len(v)!=1:return None
        values.append(v.pop())
    return tuple(values)
