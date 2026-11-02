from collections import deque,Counter
DIRS={1:(-1,0),2:(1,0),3:(0,-1),4:(0,1)}
def marks(frame,pos,n,floor,identity):
    y,x=pos;strips=[[(y-1,c)for c in range(x,x+n)],[(y+n,c)for c in range(x,x+n)],[(r,x-1)for r in range(y,y+n)],[(r,x+n)for r in range(y,y+n)]];out=[]
    boundary=Counter(frame[0]+frame[-1]+[r[0]for r in frame]+[r[-1]for r in frame]).most_common(1)[0][0]
    for side,strip in enumerate(strips):
        if not all(0<=r<64 and 0<=c<64 for r,c in strip):continue
        inks={frame[r][c]for r,c in strip}
        if len(inks)==1 and not inks&{floor,boundary,*identity}:out.append((side,next(iter(inks))))
    return out
def frontier(scene,mask,motion,known,frame,targets):
    n=scene['actor'][2];start=scene['actor'][:2];queue=deque([(start,[])]);seen={start};choices=[]
    while queue:
        p,path=queue.popleft()
        for action,(dy,dx)in DIRS.items():
            ordinary=(p[0]+dy*n,p[1]+dx*n);q=motion.get((p,action,n),ordinary)
            valid=all((y,x)in mask for y in range(q[0],q[0]+n)for x in range(q[1],q[1]+n))
            if not valid:continue
            if(p,action,n)not in motion:
                found=marks(frame,ordinary,n,scene['floor'],scene['identity'])
                if any(ink in known for _,ink in found):
                    distance=min((abs(ordinary[0]-c['box'][0])+abs(ordinary[1]-c['box'][1])for c in targets),default=0)
                    choices.append((len(path)+distance//n,p,action,path+[action],found,ordinary))
            if q not in seen:seen.add(q);queue.append((q,path+[action]))
    if not choices:return None
    _,p,action,path,found,ordinary=min(choices,key=lambda v:(v[0],len(v[3]),v[1],v[2]))
    return dict(path=path,probe_position=p,probe_action=action,expected_tile=ordinary,marks=found,hypothesis='test_unobserved_contact_with_previously_surprising_edge_appearance')
