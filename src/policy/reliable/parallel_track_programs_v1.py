"""Generic simultaneous parallel-line shift hypotheses from visible geometry."""
from collections import defaultdict
from itertools import product

def hypotheses(scene):
    cells=scene['cells'];n=len(cells);size=scene['size'];result={}
    for axis in (0,1):
        lines=defaultdict(list)
        for i,b in enumerate(cells):lines[b[1-axis]].append(i)
        maximal=[]
        for indexes in lines.values():
            indexes=tuple(sorted(indexes,key=lambda i:cells[i][axis]))
            if len(indexes)>=3:maximal.append(indexes)
        segmented=[]
        for track in scene['tracks']:
            if len({cells[i][1-axis] for i in track})==1:
                segmented.append(tuple(track))
        for tracks in (sorted(maximal),sorted(set(segmented))):
            # Bounded compositional vocabulary. Do not assume a displayed
            # control acts on every line or shares the direction of its peers.
            if not 1<=len(tracks)<=4:continue
            if len(set(i for t in tracks for i in t))!=sum(map(len,tracks)):continue
            for shifts in product((-2,-1,0,1,2),repeat=len(tracks)):
                if not any(shifts):continue
                perm=list(range(n));program=[]
                for track,k in zip(tracks,shifts):
                    if not k:continue
                    for j,dest in enumerate(track):perm[dest]=track[(j+k)%len(track)]
                    program.append(dict(track=track,shift=k))
                result[tuple(perm)]=dict(axis=axis,parallel_program=program)
    return result
