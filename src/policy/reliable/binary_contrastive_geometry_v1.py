"""Source-bound single-command contrasts after an observed program failure."""
import copy
from binary_animation_learning_v8 import bit_groups, columns, components, heading, target_scene
from binary_goal_anchored_tracking_v2 import track
from binary_rolling_program_v1 import long_route

def J(value):
    import json
    return json.loads(json.dumps(value))

def controls(raw, values, background):
    pairs = bit_groups(raw['frame'], values).get(background, [])
    return pairs, columns(pairs), target_scene(raw['frame'], pairs)

def failed_moves(trial, values, background):
    pairs, cs, scene = controls(trial['before'], values, background)
    if not scene or len(trial['after'].get('animation_frames', [])) != len(cs)+2:
        return []
    poses = [track(f, pairs, scene) for f in trial['after']['animation_frames']]
    failures = []
    for i, word in enumerate(trial['program']):
        if not any(word) or poses[i] is None:
            continue
        if poses[i+1] is None or poses[i+1]['box'] == poses[i]['box']:
            failures.append(dict(source=trial['source'], column=i, word=word,
                                 before=poses[i], after=poses[i+1],
                                 kind='literal_absence_or_unchanged_pose_not_causal_proof'))
    return failures

def unseen_contrasts(failures, known_models, trials):
    known = {tuple(m['word']) for m in known_models}
    tried = {tuple(t['query_word']) for t in trials if t['mode']=='query'}
    choices = {}
    for failure in reversed(failures):
        source_word = tuple(failure['word'])
        for row in range(len(source_word)):
            for bit in (1, 2):
                candidate = list(source_word)
                candidate[row] ^= bit
                word = tuple(candidate)
                if word in known or word in tried:
                    continue
                choices.setdefault(word, dict(word=word, failure=failure, flipped_row=row, flipped_bit=bit))
    return [choices[word] for word in sorted(choices)]

def execution_effects(trial, values, background):
    pairs, cs, scene = controls(trial['before'], values, background)
    frames = trial['after'].get('animation_frames', [])
    if not scene or len(frames) != len(cs)+2:
        return []
    poses = [track(f, pairs, scene) for f in frames]
    result = []
    for i, word in enumerate(trial['program']):
        before, after = poses[i:i+2]
        if before is None or after is None:
            continue
        result.append(dict(source=trial['source'], column=i, word=word, before=before, after=after,
                           delta=[after['box'][k]-before['box'][k] for k in (0,1)],
                           heading_before=heading(before), heading_after=heading(after),
                           generalization_is_hypothesis=True))
    return result

def select_program(raw, values, background, known_models, failures, trials):
    pairs, cs, scene = controls(raw, values, background)
    if not scene or not cs:
        return None
    neutral = next((tuple(m['word']) for m in reversed(known_models) if m['before']==m['after']), None)
    if neutral is None:
        return None
    # Only try a route after a contrast has supplied a new nonzero translation.
    learned = []
    for trial in trials:
        if trial['mode'] != 'query':
            continue
        for effect in execution_effects(trial, values, background):
            if effect['column']==0 and any(effect['delta']) and effect['before']['box'][2:]==effect['after']['box'][2:] and effect['before']['ink']==effect['after']['ink'] and effect['heading_before']==effect['heading_after']:
                learned.append(effect)
    routes = [t for t in trials if t['mode']=='route']
    if learned and len(routes)<2:
        # Context-specific current-level demonstrations plus literal new effects.
        current_models = [m for m in known_models if m.get('retained_level')==raw['levels_completed'] or tuple(m['word'])==neutral]
        models = {i:m for i,m in enumerate(current_models+learned)}
        blocked = [(tuple(f['before']['box'][:2]), tuple(f['word'])) for f in failures]
        for trial in trials:
            blocked += [(tuple(f['before']['box'][:2]), tuple(f['word'])) for f in failed_moves(trial,values,background)]
        plan = long_route(raw['frame'],scene,models,len(cs),blocked)
        new_words = {tuple(m['word']) for m in learned}
        if plan and any(tuple(w) in new_words for w in plan['program']) and not any(J(t['program'])==J(plan['program']) and J(t['scene']['actor'])==J(scene['actor']) for t in routes):
            return dict(mode='route',program=plan['program'],scene=scene,route=plan,
                        learned_effects=learned,neutral=neutral)
    choices = unseen_contrasts(failures, known_models, trials)
    if len([t for t in trials if t['mode']=='query'])>=6 or not choices:
        return None
    chosen = choices[0]
    return dict(mode='query',query_word=chosen['word'],program=[chosen['word']]+[neutral]*(len(cs)-1),
                scene=scene,contrast=chosen,neutral=neutral)

def next_click(raw, values, background, program):
    pairs, cs, scene = controls(raw, values, background)
    if not cs or len(cs)!=len(program):
        return None
    for desired, column in zip(program, cs):
        for code, pair in zip(desired, column):
            for bit, obj in enumerate(pair):
                if obj['ink'] != values[(code>>bit)&1]:
                    y,x,h,w=obj['box']
                    return dict(stage='write',data=dict(x=x+(w-1)//2,y=y+(h-1)//2),literal=obj)
    line=max(a['box'][0] for a,b in pairs)
    buttons=[o for o in components(raw['frame']) if 5<=min(o['box'][2:])<=max(o['box'][2:])<=12 and o['box'][0]>line+4 and len(o['shape'])>25]
    if not buttons:
        return None
    obj=max(buttons,key=lambda o:len(o['shape']));y,x,h,w=obj['box']
    return dict(stage='submit',data=dict(x=x+(w-1)//2,y=y+(h-1)//2),literal=obj)
