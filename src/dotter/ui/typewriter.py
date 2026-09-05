"""Typewriter reveal engine with BBCode rich text parsing and pacing tags."""

import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class TextChar:
    """A single visible character."""

    char: str


@dataclass(frozen=True, slots=True)
class WaitClickToken:
    """Pacing tag '{w}' requiring player click to continue."""


@dataclass(frozen=True, slots=True)
class PauseToken:
    """Pacing tag '{p=N}' pausing reveal for N seconds."""

    duration: float


@dataclass(frozen=True, slots=True)
class StylePushToken:
    """BBCode opening tag ('[b]', '[color=red]', etc.)."""

    tag: str
    value: str | None = None


@dataclass(frozen=True, slots=True)
class StylePopToken:
    """BBCode closing tag ('[/b]', '[/color]', etc.)."""

    tag: str


type TypewriterToken = TextChar | WaitClickToken | PauseToken | StylePushToken | StylePopToken

TAG_PATTERN = re.compile(r"(\{w\}|\{p=[\d.]+\}|\[/?[a-zA-Z]+(?:=[^\]]+)?\])")
VAR_PATTERN = re.compile(r"\{([a-zA-Z_]\w*)\}")


def _interpolate_variables(text: str, variables: dict[str, Any] | None) -> str:
    if not variables:
        return text

    def repl(m: re.Match[str]) -> str:
        var_name = m.group(1)
        if var_name == "w" or var_name.startswith("p="):
            return m.group(0)
        return str(variables.get(var_name, m.group(0)))

    return VAR_PATTERN.sub(repl, text)


def _parse_tag(raw: str) -> TypewriterToken | None:
    if raw == "{w}":
        return WaitClickToken()
    if raw.startswith("{p=") and raw.endswith("}"):
        try:
            sec = float(raw[3:-1])
            return PauseToken(duration=sec)
        except ValueError:
            return None

    if raw.startswith("[/") and raw.endswith("]"):
        return StylePopToken(tag=raw[2:-1].lower())

    if raw.startswith("[") and raw.endswith("]"):
        inner = raw[1:-1]
        if "=" in inner:
            tag, val = inner.split("=", 1)
            return StylePushToken(tag=tag.lower(), value=val)
        return StylePushToken(tag=inner.lower())

    return None


def tokenize_text(text: str, variables: dict[str, Any] | None = None) -> list[TypewriterToken]:
    """Parse text with variable interpolation, BBCode tags, and pacing into tokens."""
    expanded = _interpolate_variables(text, variables)
    tokens: list[TypewriterToken] = []

    parts = TAG_PATTERN.split(expanded)
    for part in parts:
        if not part:
            continue
        parsed_tag = _parse_tag(part)
        if parsed_tag is not None:
            tokens.append(parsed_tag)
        else:
            tokens.extend(TextChar(c) for c in part)

    return tokens


class Typewriter:
    """Character-by-character typewriter reveal engine with wait tags and pauses."""

    def __init__(self, chars_per_second: float = 40.0) -> None:
        self.chars_per_second = max(1.0, chars_per_second)
        self._tokens: list[TypewriterToken] = []
        self._index = 0
        self._elapsed = 0.0
        self._pause_timer = 0.0
        self.is_waiting_for_click = False
        self.visible_text = ""

    @property
    def is_complete(self) -> bool:
        """True if all characters in the active text stream have been revealed."""
        return self._index >= len(self._tokens) and not self.is_waiting_for_click

    def set_text(self, text: str, variables: dict[str, Any] | None = None) -> None:
        """Initialize typewriter with a fresh dialogue string."""
        self._tokens = tokenize_text(text, variables)
        self._index = 0
        self._elapsed = 0.0
        self._pause_timer = 0.0
        self.is_waiting_for_click = False
        self.visible_text = ""

    def append_text(self, text: str, variables: dict[str, Any] | None = None) -> None:
        """Append subsequent text beat into current typewriter stream."""
        new_tokens = tokenize_text(text, variables)
        self._tokens.extend(new_tokens)
        self.is_waiting_for_click = False

    def _process_current_token(self) -> bool:
        token = self._tokens[self._index]
        self._index += 1

        match token:
            case TextChar(c):
                self.visible_text += c
                return True
            case WaitClickToken():
                self.is_waiting_for_click = True
                return False
            case PauseToken(dur):
                self._pause_timer = dur
                return False
            case _:
                return False

    def update(self, dt: float) -> None:
        """Advance typewriter reveal by delta time."""
        if self.is_complete or self.is_waiting_for_click:
            return

        if self._pause_timer > 0.0:
            self._pause_timer -= dt
            if self._pause_timer > 0.0:
                return
            self._pause_timer = 0.0

        sec_per_char = 1.0 / self.chars_per_second
        self._elapsed += dt

        while (
            self._elapsed >= sec_per_char and not self.is_complete and not self.is_waiting_for_click
        ):
            consumed_char = self._process_current_token()
            if consumed_char:
                self._elapsed -= sec_per_char
            if self._pause_timer > 0.0:
                break

    def click(self) -> bool:
        """Handle click: resume from wait click, skip to end, or signal complete."""
        if self.is_waiting_for_click:
            self.is_waiting_for_click = False
            return True

        if not self.is_complete:
            self.skip_to_end()
            return True

        return False

    def skip_to_end(self) -> None:
        """Instantly reveal all remaining characters up to end or next wait tag."""
        while self._index < len(self._tokens):
            token = self._tokens[self._index]
            if isinstance(token, WaitClickToken):
                self._index += 1
                self.is_waiting_for_click = True
                break
            if isinstance(token, TextChar):
                self.visible_text += token.char
            self._index += 1

        self._pause_timer = 0.0
        self._elapsed = 0.0
