"""Make a bounded entry into active tool discovery after observed passive failure."""
import copy,hashlib,pickle,json
from graph_state_semantics_v3 import normalized
from conditional_disjoint_tool_learner import Learner
from completion_tool_word_handoff import unowned_legacy
from visual_transform_learner import public


def identity(value):
    return hashlib.sha256(json.dumps(normalized(value),separators=(',',':'),ensure_ascii=True,allow_nan=False).encode()).hexdigest()


class Controller:
    def __init__(self, prior, *, retain=True):
        self.prior = prior
        self.learner = Learner(retain=retain)
        self.active = False
        self.last = None
        self.data = {}
        self.handoff = None
        self.steps = 0
        self.passive_attempts = 0
        self.passive_level = None
        self.unchanged_actions = []
        self.observed_events=0
        self.flat_valid=False
        self.flat_count=0
        self.entry_index=None
        self.entry_parent_identity=None
        self.blocked_level=None
        self.blocked_edits=0
        self.resumptions=[]

    def respond(self, raw):
        obs = public(raw)
        previous = self.learner.previous
        if previous is not None and self.last is not None:
            self.observed_events+=1
        if self.active and self.flat_valid:
            self.flat_valid=(self.last not in (None,0) and previous==obs==self.handoff['observation'])
            if self.flat_valid:self.flat_count+=1
        if previous is not None and self.last is not None and not self.active:
            if (self.last != 0 and previous["state"] == obs["state"] == "NOT_FINISHED"
                    and previous["levels_completed"] == obs["levels_completed"]
                    and previous["frame"] == obs["frame"]):
                self.unchanged_actions = (self.unchanged_actions + [self.last])[-32:]
            else:
                self.unchanged_actions = []
        if obs["levels_completed"] != self.passive_level:
            self.passive_attempts = 0
            self.passive_level = obs["levels_completed"]
        elif not self.active and self.last not in (None, 0) and obs["state"] == "NOT_FINISHED":
            self.passive_attempts += 1
        self.learner.observe(obs, self.last, self.data)
        if (self.active and self.flat_valid and self.flat_count>=64
                and self.handoff['admission']=='active_discovery_after_passive_attempts'):
            assert obs==self.handoff['observation']
            assert identity(self.prior)==self.entry_parent_identity
            record=dict(kind='observed_noop_handback',start=self.entry_index,end=self.observed_events,
                observed_unchanged_events=self.flat_count,observation=copy.deepcopy(obs),
                parent_state_identity=self.entry_parent_identity,
                scope='Deliver the saved actual outcome of the paused expert last action only when the entire intervening attempt preserved the four-field observation. No equivalence of unobserved state is asserted.')
            assert record['end']-record['start']==self.flat_count
            self.active=False
            self.blocked_level=obs['levels_completed']
            self.blocked_edits=sum(self.learner.edited.values())
            self.flat_valid=False
            response=self.prior.respond(obs)
            record['selected_parent_response']=copy.deepcopy(response)
            self.resumptions.append(record)
            self.last=response['action'];self.data=copy.deepcopy(response['data'])
            return response
        if (self.blocked_level is not None and (obs['levels_completed']!=self.blocked_level
                or sum(self.learner.edited.values())>self.blocked_edits)):
            self.blocked_level=None
        graph = getattr(self.prior, "controller", None)
        stalled_spatial = (self.prior.spatial is True and not getattr(graph, "active", False)
            and len(self.unchanged_actions) == 32 and len(set(self.unchanged_actions)) >= 3
            and bool(self.learner.sources))
        candidate = self.learner.propose(obs) if self.active or self.blocked_level is None and (unowned_legacy(self.prior) or stalled_spatial) else None
        supported = candidate and candidate.get("goal") and any(self.learner.edited.values())
        # No editable-word success is claimed at this admission. The learner
        # is explicitly taking an experiment, after 32 actual passive attempts.
        discovery = (candidate and candidate["phase"] == "select"
            and not candidate.get("goal") and not any(self.learner.edited.values())
            and self.passive_attempts >= 32 and len(self.learner.rows) >= 2)
        if not self.active and (supported or discovery):
            self.active = True
            self.flat_valid=True
            self.flat_count=0
            self.entry_index=self.observed_events
            self.entry_parent_identity=identity(self.prior)
            self.handoff = dict(observation=copy.deepcopy(obs), preceding_actual_action=self.last,
                preceding_actual_data=copy.deepcopy(self.data), certificate=copy.deepcopy(candidate),
                admission="observed_editable_word" if supported else "stalled_spatial_active_discovery" if stalled_spatial else "active_discovery_after_passive_attempts",
                unchanged_actions=copy.deepcopy(self.unchanged_actions),
                actual_passive_attempts=self.passive_attempts,
                prior_resumption_rule="Paused intact. A discovery-only attempt may return after64actual events preserve the complete handoff observation; deliver its saved actual outcome before selecting a new expert action. No invented outcomes.")
        if not self.active:
            response = self.prior.respond(obs)
        else:
            if candidate:
                self.learner.commit(candidate)
            action = candidate["action"] if candidate else None
            data = candidate["data"] if candidate else {}
            self.steps += int(action is not None)
            response = dict(done=action is None, action=0 if action is None else action, data=data,
                advisor="retained_tool_word_stalled_discovery", certificate=candidate,
                diagnostics=dict(tool_word_actions=self.steps, actual_model_calls=0,
                    retained_goal_sources=len(self.learner.sources),
                    observed_pair_effects=sum(map(len, self.learner.models.values()))))
        self.last = response["action"]
        self.data = copy.deepcopy(response["data"])
        return response
