"""Keep the same word equations while treating each displayed rule word as a control unit."""
from editable_word_programs import layouts,signature,solutions
from panel_control_learner import identity

def values(layout):
    return tuple((p['background'],tuple(identity(g['mask']) for g in p['symbols'])) for p in layout['panels'])

def proposals(layout,query):
    parsed=solutions(query['source'],query['target'],layout['schema'])
    if parsed['overflow']:return [],True
    result=[]
    for program,derivation in parsed['programs']:
        expected={}
        for (a,b),(left,right) in zip(layout['pairs'],program):
            expected[tuple(a['box'])]=left;expected[tuple(b['box'])]=right
        cells=[];classes=[];goal=[]
        for panel in layout['panels']:
            cells.append(dict(box=panel['box'],index=None,background=panel['background'],word_length=len(panel['symbols'])))
            classes.append((panel['background'],tuple(identity(g['mask']) for g in panel['symbols'])))
            goal.append((panel['background'],expected[tuple(panel['box'])]))
        box=(min(p['box'][0] for p in layout['panels']),min(p['box'][1] for p in layout['panels']),
             max(p['box'][2] for p in layout['panels']),max(p['box'][3] for p in layout['panels']))
        proof=dict(kind='editable_word_program',control_unit='panel_word',query=query,
            source_background=layout['source_background'],target_background=layout['target_background'],
            schema=layout['schema'],rule_boxes=[(a['box'],b['box']) for a,b in layout['pairs']],
            program=program,derivation=derivation,cells=cells,
            scope='Tentative word transducer. Whole displayed words are control units; coordinated edits require actual intervention evidence.')
        result.append(dict(box=box,source_box=query['source_box'],classes=tuple(classes),expected=tuple(goal),proposal=proof))
    return result,False
