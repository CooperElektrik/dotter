"""Core enumerations and type aliases for the Dotter engine."""

from enum import StrEnum

type NodeId = str


class SpritePosition(StrEnum):
    """Predefined horizontal positioning anchors for character sprites."""

    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"
    CUSTOM = "custom"


class TransitionType(StrEnum):
    """Visual transitions between scenes and visual states."""

    DISSOLVE = "dissolve"
    FADE_BLACK = "fade_black"
    FADE_WHITE = "fade_white"
    CUT = "cut"


class AudioChannel(StrEnum):
    """Dedicated audio output channels."""

    BGM = "bgm"
    VOICE = "voice"
    SFX = "sfx"
    AMB = "amb"
