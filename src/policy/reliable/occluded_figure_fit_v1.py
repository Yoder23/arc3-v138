"""Check residual visible geometry while permitting known-color overlays."""
from component_figure_model_v4 import pixels,ignore_mask
def fit_figure(fig,frame,sc,othercolors):
 expected={p for pts in pixels(fig['state'],fig['segments']) for p in pts if 0<=p[0]<62 and 0<=p[1]<64}-ignore_mask(sc);actual={(y,x) for y,row in enumerate(frame[:62]) for x,c in enumerate(row) if c==fig['color']}-ignore_mask(sc)
 if not expected or actual-expected or len(actual)<max(4,.25*len(expected)):return False
 return all(frame[y][x] in set(othercolors)|{0} for y,x in expected-actual)
