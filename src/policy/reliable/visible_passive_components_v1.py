"""Literal single-color connected components; all object roles remain hypotheses."""
def components(frame):
    seen=set();out=[]
    for y in range(64):
        for x in range(64):
            if (y,x) in seen:continue
            ink=frame[y][x];todo=[(y,x)];seen.add((y,x));cells=[]
            while todo:
                a,b=todo.pop();cells.append((a,b))
                for q in ((a-1,b),(a+1,b),(a,b-1),(a,b+1)):
                    if 0<=q[0]<64 and 0<=q[1]<64 and q not in seen and frame[q[0]][q[1]]==ink:seen.add(q);todo.append(q)
            yy=min(a for a,b in cells);xx=min(b for a,b in cells);h=max(a for a,b in cells)-yy+1;w=max(b for a,b in cells)-xx+1
            out.append(dict(ink=ink,box=(yy,xx,h,w),shape=tuple(sorted((a-yy,b-xx) for a,b in cells))))
    return out
