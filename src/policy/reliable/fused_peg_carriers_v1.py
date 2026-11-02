def scan(frame,size,ink,source=None):
 n=size+2;shape=[(dy,dx)for dy in range(n)for dx in range(n)if dy in(0,n-1)or dx in(0,n-1)];out=[]
 for y in range(65-n):
  for x in range(65-n):
   if frame[y][x]!=ink or not all(frame[y+dy][x+dx]==ink for dy,dx in shape):continue
   if all(frame[y+dy][x+dx]==ink for dy in range(1,n-1)for dx in range(1,n-1)):continue
   body=dict(ink=ink,box=(y,x,n,n),shape=shape)
   if source is not None:body['fused_template_source']=source
   out.append(body)
 return out
