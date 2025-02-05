from enum import Enum

class StateKeys(Enum):
    PLAY_STATE = 'playState'
    CURRENT_TRACK = 'currentTrack'
    SETTINGS = 'settings'

class Commands(Enum):
    PLAY_NEXT = 'playNext'
    PLAY_PREVIOUS = 'playPrevious'
    PLAY_ALBUM = 'playAlbum'
    FAST_FORWARD = 'forwards'
    REWIND = 'reverse'
    SEEK = 'seek'
