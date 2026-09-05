import re
from dataclasses import dataclass

CHOICE_PATTERN = re.compile(r"^\?\s+(.*?)\s*\(([^)]+)\)\s*$")
VOICE_PATTERN = re.compile(r"^\{voice:([^}]+)\}\s*")


class ParseError(Exception):
    """Raised when screenplay syntax is invalid."""

    def __init__(self, message: str, line_number: int) -> None:
        super().__init__(f"Line {line_number}: {message}")
        self.line_number = line_number


@dataclass(frozen=True, slots=True)
class ParsedLabel:
    """Parsed section label."""

    name: str
    display_name: str
    line_number: int


@dataclass(frozen=True, slots=True)
class ParsedDialogue:
    """Parsed character dialogue beat."""

    speaker: str
    text: str
    voice: str | None
    line_number: int


@dataclass(frozen=True, slots=True)
class ParsedAppend:
    """Parsed append beat ('-')."""

    text: str
    line_number: int


@dataclass(frozen=True, slots=True)
class ParsedFreshBox:
    """Parsed fresh box beat ('/')."""

    text: str
    line_number: int


@dataclass(frozen=True, slots=True)
class ParsedNarration:
    """Parsed speakerless narration."""

    text: str
    line_number: int


@dataclass(frozen=True, slots=True)
class ParsedChoiceOption:
    """Parsed choice menu option ('?')."""

    text: str
    target: str
    line_number: int


@dataclass(frozen=True, slots=True)
class ParsedChoiceSet:
    """Parsed collection of consecutive choice options."""

    options: tuple[ParsedChoiceOption, ...]
    line_number: int


@dataclass(frozen=True, slots=True)
class ParsedJump:
    """Parsed unconditional jump ('>')."""

    target: str
    line_number: int


@dataclass(frozen=True, slots=True)
class ParsedCall:
    """Parsed subroutine call ('>>')."""

    target: str
    line_number: int


@dataclass(frozen=True, slots=True)
class ParsedReturn:
    """Parsed subroutine return ('<<')."""

    line_number: int


@dataclass(frozen=True, slots=True)
class ParsedHook:
    """Parsed hook invocation ('~')."""

    hook_name: str
    line_number: int


type ParsedItem = (
    ParsedLabel
    | ParsedDialogue
    | ParsedAppend
    | ParsedFreshBox
    | ParsedNarration
    | ParsedChoiceSet
    | ParsedJump
    | ParsedCall
    | ParsedReturn
    | ParsedHook
)


def _slugify(text: str) -> str:
    """Convert display name into a snake_case identifier."""
    slug = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "_", slug)


def _parse_label(line: str, line_number: int) -> ParsedLabel:
    """Parse a label definition ('## Name --- id' or '## Name')."""
    rest = line[2:].strip()
    if not rest:
        raise ParseError("Empty label definition", line_number)
    if "---" in rest:
        display, name = rest.split("---", 1)
        return ParsedLabel(name=name.strip(), display_name=display.strip(), line_number=line_number)
    return ParsedLabel(name=_slugify(rest), display_name=rest, line_number=line_number)


def _parse_choice(line: str, line_number: int) -> ParsedChoiceOption:
    """Parse a single choice line ('? Option text (target_label)')."""
    match = CHOICE_PATTERN.match(line)
    if not match:
        raise ParseError(
            "Invalid choice syntax. Expected '? Text (target_label)'",
            line_number,
        )
    return ParsedChoiceOption(
        text=match.group(1).strip(),
        target=match.group(2).strip(),
        line_number=line_number,
    )


def _parse_dialogue(speaker: str, raw_text: str, line_number: int) -> ParsedDialogue:
    """Extract optional voice tag and return ParsedDialogue."""
    voice: str | None = None
    text = raw_text.strip()
    voice_match = VOICE_PATTERN.match(text)
    if voice_match:
        voice = voice_match.group(1).strip()
        text = text[voice_match.end() :].strip()
    return ParsedDialogue(speaker=speaker, text=text, voice=voice, line_number=line_number)


def _strip_line_comment(line: str) -> str:
    """Strip comments starting with '#' unless escaped or part of label '##'."""
    if line.startswith("##"):
        return line
    if "#" in line:
        return line.split("#", 1)[0].rstrip()
    return line


class ScreenplayParser:
    """Parses inProse screenplay text into a sequence of parsed AST items."""

    def __init__(self) -> None:
        self._items: list[ParsedItem] = []
        self._narration_buffer: list[str] = []
        self._narration_line = 0
        self._choice_buffer: list[ParsedChoiceOption] = []

    def _flush_narration(self) -> None:
        if self._narration_buffer:
            combined = " ".join(self._narration_buffer)
            self._items.append(ParsedNarration(text=combined, line_number=self._narration_line))
            self._narration_buffer.clear()

    def _flush_choices(self) -> None:
        if self._choice_buffer:
            first_line = self._choice_buffer[0].line_number
            self._items.append(
                ParsedChoiceSet(options=tuple(self._choice_buffer), line_number=first_line)
            )
            self._choice_buffer.clear()

    def _flush_all(self) -> None:
        self._flush_narration()
        self._flush_choices()

    def _parse_prefixed(self, line: str, line_number: int) -> None:
        if line.startswith("##"):
            self._items.append(_parse_label(line, line_number))
        elif line.startswith(">>"):
            self._items.append(ParsedCall(target=line[2:].strip(), line_number=line_number))
        elif line.startswith("<<"):
            self._items.append(ParsedReturn(line_number=line_number))
        elif line.startswith(">"):
            self._items.append(ParsedJump(target=line[1:].strip(), line_number=line_number))
        elif line.startswith("~"):
            self._items.append(ParsedHook(hook_name=line[1:].strip(), line_number=line_number))
        elif line.startswith("-"):
            self._items.append(ParsedAppend(text=line[1:].strip(), line_number=line_number))
        elif line.startswith("/"):
            self._items.append(ParsedFreshBox(text=line[1:].strip(), line_number=line_number))

    def _process_line(self, raw_line: str, line_number: int) -> None:
        clean = _strip_line_comment(raw_line.strip())
        if not clean:
            self._flush_all()
            return

        if clean.startswith("?"):
            self._flush_narration()
            self._choice_buffer.append(_parse_choice(clean, line_number))
            return

        self._flush_choices()

        if clean.startswith(("##", ">", "<", "~", "-", "/")):
            self._flush_narration()
            self._parse_prefixed(clean, line_number)
            return

        if ":" in clean:
            speaker, text = clean.split(":", 1)
            if speaker.strip() and not any(c in speaker for c in "#?><~/"):
                self._flush_narration()
                self._items.append(_parse_dialogue(speaker.strip(), text, line_number))
                return

        if not self._narration_buffer:
            self._narration_line = line_number
        self._narration_buffer.append(clean)

    def parse(self, text: str) -> list[ParsedItem]:
        """Parse screenplay text into a list of parsed items."""
        self._items.clear()
        self._narration_buffer.clear()
        self._choice_buffer.clear()

        for idx, line in enumerate(text.splitlines(), start=1):
            self._process_line(line, idx)

        self._flush_all()
        return list(self._items)
