"""Compose demonstrated dictionaries across intermediate visual alphabets."""
from collections import deque
from panel_word_hypotheses import candidates as direct,glyphs,identity
from panel_hypotheses_v2 import digest

def translate(source,mapping,cap=128,max_length=16):
    states={(0,()):()}
    for index in range(len(source)):
        for (at,output),derivation in list(states.items()):
            if at!=index:continue
            for word,target in sorted(mapping.items()):
                end=at+len(word)
                if source[at:end]!=word or len(output)+len(target)>max_length:continue
                key=end,output+target;candidate=derivation+((at,end,word,target),)
                if key not in states or len(candidate)<len(states[key]):states[key]=candidate
                if len(states)>cap:return [],True
    return sorted([(output,d) for (at,output),d in states.items() if at==len(source)],
                  key=lambda p:(len(p[1]),p[0])),False

def candidates(obs,remembered=()):
    parsed=direct(obs,remembered);maps=parsed['maps'] or list(remembered)
    if len({m['source_background'] for m in maps}|{m['target_background'] for m in maps})<3:
        return parsed
    proof=digest(obs);rects=parsed['rectangles'];proposals=list(parsed['proposals'])
    used={tuple(e[k]) for m in maps for e in m['examples'] if e['observation']==proof for k in ('source_box','target_box')}
    for left in rects:
        if left['box'] in used or len(left['symbols'])<2:continue
        for right in rects:
            if right['box'] in used or left['background']==right['background']:continue
            a,b,c,d=left['box'];y,x,Y,X=right['box'];h=c-a+1;w=d-b+1;H=Y-y+1;W=X-x+1
            axis='horizontal' if w>h and W>H and h==H and abs(b+d-x-X)<=1 else 'vertical' if h>w and H>W and w==W and abs(a+c-y-Y)<=1 else None
            if axis is None:continue
            word=tuple(identity(g['mask']) for g in left['symbols'])
            queue=deque([(left['background'],word,(),(left['background'],))]);seen=set();found={}
            while queue and len(seen)<128:
                background,current,stages,visited=queue.popleft()
                key=background,current,visited
                if key in seen:continue
                seen.add(key)
                if background==right['background']:
                    if len(stages)>=2 and len(current)==len(right['symbols']):
                        found.setdefault(current,stages)
                    continue
                if len(stages)>=3:continue
                for m in maps:
                    if m['source_background']!=background or m['axis']!=axis or m['target_background'] in visited:continue
                    outputs,overflow=translate(current,m['mapping'])
                    parsed['truncated']+=int(overflow)
                    for output,derivation in outputs:
                        stage=dict(source_background=background,target_background=m['target_background'],
                            input=current,output=output,derivation=derivation,examples=m['examples'])
                        queue.append((m['target_background'],output,stages+(stage,),visited+(m['target_background'],)))
            if queue:
                parsed['truncated']+=1
                continue
            for expected,stages in sorted(found.items(),key=lambda p:(len(p[1]),p[0])):
                proposals.append(dict(kind='visual_dictionary_chain',source_box=left['box'],target_box=right['box'],
                    source_background=left['background'],target_background=right['background'],
                    actual=tuple(g['mask'] for g in right['symbols']),expected=expected,stages=stages,
                    examples=[e for s in stages for e in s['examples']],observation=proof,
                    derivation=tuple(d for s in stages for d in s['derivation']),alternatives=len(found),
                    scope='Tentative bounded composition of demonstrated dictionaries across distinct alphabets; every intermediate word has historical pixel support. Actual progress decides sufficiency.'))
    parsed['proposals']=proposals
    return parsed
