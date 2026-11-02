"""Portable complete components for independent visual checks."""
def parts(f):
 seen=set();out=[];H=len(f);W=len(f[0])
 for color in sorted({v for row in f for v in row}):
  for y in range(H):
   for x in range(W):
    if f[y][x]!=color or (y,x) in seen:continue
    seen.add((y,x));q=[(y,x)]
    for a,b in q:
     for u,v in ((a-1,b),(a+1,b),(a,b-1),(a,b+1)):
      if 0<=u<H and 0<=v<W and f[u][v]==color and (u,v) not in seen:seen.add((u,v));q.append((u,v))
    top=min(a for a,b in q);left=min(b for a,b in q);bottom=max(a for a,b in q);right=max(b for a,b in q)
    if top==0 or left==0 or bottom==H-1 or right==W-1:continue
    out.append(dict(color=color,area=len(q),y=top,x=left,h=bottom-top+1,w=right-left+1,shape=tuple((a-top,b-left) for a,b in sorted(q))))
 return out
