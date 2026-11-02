"""Read three-by-three reference masks from framed visible pixel panels."""
from collections import deque

def programs(frame,grid):
    if not grid or len(grid['cells'])!=9:return []
    y,x,h,w=grid['cells'][0];border=frame[y][x+w];seen=set();out=[]
    for y in range(64):
        for x in range(64):
            if (y,x) in seen or frame[y][x]!=border:continue
            todo=[(y,x)];seen.add((y,x));pixels=[]
            while todo:
                a,b=todo.pop();pixels.append((a,b))
                for q in ((a-1,b),(a+1,b),(a,b-1),(a,b+1)):
                    if 0<=q[0]<64 and 0<=q[1]<64 and q not in seen and frame[q[0]][q[1]]==border:seen.add(q);todo.append(q)
            yy=min(a for a,b in pixels);xx=min(b for a,b in pixels);hh=max(a for a,b in pixels)-yy+1;ww=max(b for a,b in pixels)-xx+1
            if hh!=ww or not 7<=hh<=25 or (hh-1)%3:continue
            pitch=(hh-1)//3;size=pitch-1
            if not all(frame[yy][b]==frame[yy+hh-1][b]==border for b in range(xx,xx+ww)) or not all(frame[a][xx]==frame[a][xx+ww-1]==border for a in range(yy,yy+hh)):continue
            gaps=[frame[a][b] for a in range(yy+1,yy+hh-1) for b in range(xx+1,xx+ww-1) if (a-yy-1)%pitch==size or (b-xx-1)%pitch==size]
            if len(set(gaps))!=1 or gaps[0]==border:continue
            background=gaps[0];cells=[];valid=True
            for i in range(9):
                a=yy+1+i//3*pitch;b=xx+1+i%3*pitch;values={frame[v][u] for v in range(a,a+size) for u in range(b,b+size)}
                if len(values)!=1:valid=False;break
                cells.append(dict(box=(a,b,size,size),ink=next(iter(values))))
            if not valid:continue
            for ink in sorted({c['ink'] for c in cells}-{background,border}):
                indices=[i for i,c in enumerate(cells) if c['ink']==ink]
                out.append(dict(panel=(yy,xx,hh,ww),border=border,background=background,pitch=pitch,cell_size=size,cells=cells,ink=ink,indices=indices,hypothesis='visible_reference_mask_may_specify_an_input_program'))
    return sorted(out,key=lambda p:(p['panel'],p['ink']))
