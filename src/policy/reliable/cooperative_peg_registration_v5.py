"""Infer camera translation from repeated visible terrain and retain its coordinates."""
from collections import Counter
from cooperative_peg_perception_v6 import retained_scene as scene
def alignment(before,after,dy,dx):
    bg=Counter(v for row in before[3:]for v in row).most_common(1)[0][0];same=total=0
    for y in range(max(3,3+dy),min(64,64+dy)):
        for x in range(max(0,dx),min(64,64+dx)):
            a=before[y][x];b=after[y-dy][x-dx]
            if a==bg and b==bg:continue
            total+=1;same+=a==b
    return same,total
def infer(before,after,template=None):
    a=scene(before,template);b=scene(after,template)
    if not a or not b or a['size']!=b['size']or a['field']!=b['field']:return dict(delta=(0,0),supported=False)
    shifts=Counter((y-yy,x-xx)for y,x in a['cells']for yy,xx in b['cells']if abs(y-yy)<64 and abs(x-xx)<64)
    candidates={(0,0)}|{d for d,n in shifts.items()if n>=3};rank=[]
    for d in candidates:
        same,total=alignment(before,after,*d)
        if total>=120:rank.append((same/total,d,same,total))
    rank.sort(reverse=True)
    if not rank:return dict(delta=(0,0),supported=False)
    best=rank[0];zero=next((r[0]for r in rank if r[1]==(0,0)),0.);second=rank[1][0]if len(rank)>1 else 0.
    supported=best[1]!=(0,0)and best[0]>=.8 and best[0]-zero>=.1 and best[0]-second>=.04
    return dict(delta=best[1]if supported else(0,0),supported=supported,agreement=best[0],unshifted_agreement=zero,runner_up=second,matched=best[2],compared=best[3])
