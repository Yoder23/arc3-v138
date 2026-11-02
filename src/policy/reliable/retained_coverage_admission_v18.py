from binary_checkpoint_temporal_inquiry_v1 import Agent as BinaryTemporal
from binary_rolling_admission_v1 import route as binary_route
import beam_split_learner_v5
from waypoint_measured_range_v3 import Agent as Waypoint
from waypoint_admission_v1 import route as waypoint_route
"""Visible contracts select retained timing, transport, or encounter learning."""
from animated_switch_navigation_v20 import Agent as Switch,scene as switch_scene
from coupled_marker_alignment_v13 import Agent as Marker,scene as marker_scene
from directional_encounter_learner_v6 import Agent as Encounter,perception
from beam_split_learner_v20 import Agent as Beam
from beam_split_geometry_v3 import perceive as beam_scene

import key_glyph_learning_v20
from key_glyph_learning_v23 import Agent as Key,perceive as key_scene
from carry_material_transfer_v4 import Controller as Carry
from carry_admission_v2 import admissible as carry_scene

from cooperative_peg_learning_v15 import Agent as Peg
from peg_jump_inquiry_v2 import scene as peg_scene

def route(raw):
    actions=set(raw['available_actions'])
    if actions=={1,2,3,4,5}and switch_scene(raw['frame']):return 'animated_switch'
    if actions=={6}and marker_scene(raw['frame']):return 'coupled_marker'
    if actions=={1,2,3,4}and perception(raw['frame']):return 'directional_encounter'
    if actions=={1,2,3,4,5,6}and beam_scene(raw['frame']):return 'beam_split'
    if actions=={1,2,3,4}and key_scene(raw['frame']):return 'key_glyph'
    if actions=={1,2,3,4,5}and carry_scene(raw):return 'carry_material'
    if actions=={1,2,3,4,6,7}and peg_scene(raw['frame']):return 'viewport_peg'
    if waypoint_route({k:raw[k]for k in('frame','state','available_actions','levels_completed')})=='waypoint':return 'measured_waypoint'
    if binary_route(raw)=='binary_animation':return 'binary_temporal'
    return 'parent'
class Controller:
    def __init__(self,parent):self.parent=parent;self.route=None;self.expert=None
    def respond(self,raw):
        if self.route is None:
            self.route=route(raw)
            cls={'animated_switch':Switch,'coupled_marker':Marker,'directional_encounter':Encounter,'beam_split':Beam,'key_glyph':Key,'carry_material':Carry,'viewport_peg':Peg,'measured_waypoint':Waypoint,'binary_temporal':BinaryTemporal}.get(self.route)
            if cls:self.expert=cls()
        obs={k:raw[k]for k in('frame','state','available_actions','levels_completed')}if self.route in('carry_material','viewport_peg','measured_waypoint')else raw
        return self.expert.respond(obs)if self.expert else self.parent.respond(raw)
