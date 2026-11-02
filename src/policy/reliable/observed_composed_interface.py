"""Shared observation-based evidence for the composed-symbol input family."""
from composed_word_layouts import layouts
def recognized(obs):
    legal=set(obs['available_actions'])
    return (obs['state']=='NOT_FINISHED' and bool(legal) and legal<=set(range(1,6))
        and any(p.get('kind')=='composed_editable_word_layout' and p['queries'] for p in layouts(obs)))
