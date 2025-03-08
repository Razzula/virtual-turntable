"""Enum classes for the state system and commands."""
from enum import Enum


class StateKeys(Enum):
    """Keys for the state object in the state system."""
    PLAY_STATE = 'playState'
    CURRENT_TRACK = 'currentTrack'
    SETTINGS = 'settings'

class Commands(Enum):
    """Commands that can be sent to and from the server."""
    PLAY_NEXT = 'playNext'
    PLAY_PREVIOUS = 'playPrevious'
    PLAY_ALBUM = 'playAlbum'
    PLAY_PLAYLIST = 'playPlaylist'
    FAST_FORWARD = 'forwards'
    REWIND = 'reverse'
    SEEK = 'seek'
    REFRESH_PLAYLIST = 'refreshPlaylist'
