from enum import Enum

class StateKeys(Enum):
    PLAY_STATE = 'playState'
    CURRENT_TRACK = 'currentTrack'
    SETTINGS = 'settings'

class Commands(Enum):
    FAST_FORWARD = 'forwards'
    REWIND = 'reverse'
    SEEK = 'seek'
