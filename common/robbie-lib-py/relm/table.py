"""IRELM commands and the RELM to IRELM table (YAML: macro name -> IRELM string)."""
from dataclasses import dataclass, field

import yaml

from .markup import BadTag, RelmError, Tag, escape_attr, is_number, scan, strip_ws

SPANS = ("VAD", "PROSODY", "VOICE", "AS")
PARAMS = {
    "VAD": ("v", "a", "d"),
    "PROSODY": ("p", "s", "r", "v"),
    "VOICE": ("voice", "locale"),
    "AS": ("format", "locale"),
    "MESSAGE": ("sub", "action"),
    "BEEP": ("melody",),
    "AUDIO": ("file_name",),
    "PAUSE": ("duration",),
}
ALIASES = {
    "VAD": {"valence": "v", "arousal": "a", "dominance": "d"},
    "PROSODY": {"pitch": "p", "speed": "s", "range": "r", "volume": "v"},
}
REQUIRED = {
    "AS": ("format",),
    "MESSAGE": ("sub", "action"),
    "BEEP": ("melody",),
    "AUDIO": ("file_name",),
    "PAUSE": ("duration",),
}
AS_FORMATS = ("datetime", "number", "digits", "characters", "unit", "currency")


@dataclass
class Command:
    name: str
    attrs: list = field(default_factory=list)   # [(key, value)], canonical keys, table order

    @property
    def is_span(self) -> bool:
        return self.name in SPANS

    def get(self, key: str):
        for k, v in self.attrs:
            if k == key:
                return v
        return None

    def xml(self, self_closing: bool) -> str:
        attrs = "".join(f' {k}="{escape_attr(v)}"' for k, v in self.attrs)
        return f"<{self.name}{attrs}{'/' if self_closing else ''}>"


@dataclass
class Macro:
    name: str
    open: list = field(default_factory=list)    # [Command]
    close: list = field(default_factory=list)   # [Command], from the "/name" entry

    @property
    def spans(self) -> list:
        return [c for c in self.open if c.is_span]

    @property
    def instant(self) -> bool:
        """Nothing to undo, so the macro is never pushed on the stack."""
        return not self.spans and not self.close


def check_melody(melody: str):
    """Returns an error message, or None if the BEEP melody is valid."""
    notes = [strip_ws(n) for n in melody.split(";")]
    notes = [n for n in notes if n]
    if not notes:
        return "melody is empty"
    for item in notes:
        parts = [strip_ws(p) for p in item.split(",")]
        if len(parts) != 2:
            return f'"{item}" is not NOTE,DURATION'
        note, duration = parts
        ok = note == "R" or (
            2 <= len(note) <= 3 and note[0] in "ABCDEFG" and note[-1] in "012345678"
            and (len(note) == 2 or note[1] in "#b"))
        if not ok:
            return f'"{note}" is not a note (e.g. C4, C#4, Eb4 or R)'
        if not is_number(duration) or float(duration) <= 0:
            return f'"{duration}" is not a duration in seconds'
    return None


def _check_value(cmd: str, key: str, value: str):
    if cmd == "VAD":
        if value != "none" and not (is_number(value) and 1 <= float(value) <= 5):
            return f'{key}="{value}" must be 1 to 5 or "none"'
    elif cmd == "PROSODY":
        if value != "none" and not (is_number(value) and float(value) > 0):
            return f'{key}="{value}" must be a multiplier above 0 or "none"'
    elif cmd == "PAUSE":
        if not (is_number(value) and float(value) >= 0):
            return f'duration="{value}" must be seconds'
    elif cmd == "BEEP":
        return check_melody(value)
    elif cmd == "AS" and key == "format":
        if value not in AS_FORMATS:
            return f'format="{value}" must be one of {"|".join(AS_FORMATS)}'
    elif cmd in ("AUDIO", "VOICE", "AS") and not strip_ws(value):
        return f"{key} is empty"
    return None


def command_from_tag(tag: Tag) -> Command:
    """Validate a tag as an IRELM command. Raises RelmError("bad_table")."""
    if tag.closing:
        raise RelmError("bad_table", f"</{tag.name}> is not allowed, the stack closes spans")
    if tag.name not in PARAMS:
        raise RelmError("bad_table", f"unknown command <{tag.name}>")
    if tag.name in SPANS and tag.self_closing:
        raise RelmError("bad_table", f"<{tag.name}> is a span, write it as an open tag")
    if tag.name not in SPANS and not tag.self_closing:
        raise RelmError("bad_table", f"<{tag.name}> must be self-closing, e.g. <{tag.name} .../>")
    attrs = []
    for key, value in tag.attrs:
        key = ALIASES.get(tag.name, {}).get(key, key)
        if key not in PARAMS[tag.name]:
            raise RelmError("bad_table", f"<{tag.name}> has no param {key}")
        if any(k == key for k, _ in attrs):
            raise RelmError("bad_table", f"<{tag.name}> has {key} twice")
        problem = _check_value(tag.name, key, value)
        if problem:
            raise RelmError("bad_table", f"<{tag.name}> {problem}")
        attrs.append((key, value))
    for key in REQUIRED.get(tag.name, ()):
        if not any(k == key for k, _ in attrs):
            raise RelmError("bad_table", f"<{tag.name}> needs {key}")
    return Command(tag.name, attrs)


def _is_macro_name(name: str) -> bool:
    return bool(name) and name[0].isascii() and (name[0].isalpha() or name[0] == "_") and all(
        c.isascii() and (c.isalnum() or c in "_-.:") for c in name)


def _parse_entry(name: str, value: str, is_close: bool) -> list:
    commands, kinds = [], set()
    for item in scan(value):
        if isinstance(item, str):
            if strip_ws(item):
                raise RelmError("bad_table", f'{name}: text "{strip_ws(item)}" is not allowed')
            continue
        if isinstance(item, BadTag):
            raise RelmError("bad_table", f"{name}: malformed tag {item.snippet}")
        try:
            cmd = command_from_tag(item)
        except RelmError as e:
            raise RelmError("bad_table", f"{name}: {e.message}") from None
        if cmd.is_span:
            if is_close:
                raise RelmError("bad_table", f"/{name}: may only hold self-closing commands")
            if cmd.name in kinds:
                raise RelmError("bad_table", f"{name}: <{cmd.name}> appears twice")
            kinds.add(cmd.name)
        commands.append(cmd)
    if not commands:
        raise RelmError("bad_table", f"{name}: no IRELM commands")
    return commands


class _Loader(yaml.SafeLoader):
    pass


def _mapping_without_duplicates(loader, node, deep=False):
    seen = set()
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in seen:
            raise RelmError("bad_table", f"{key} is defined twice")
        seen.add(key)
    return loader.construct_mapping(node, deep)


_Loader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping_without_duplicates)


class Table:
    """The RELM to IRELM table. Each entry maps a macro name to IRELM commands; an entry
    named "/name" holds the commands sent when that macro closes."""

    def __init__(self, entries: dict):
        self.macros = {}
        closes = {}
        for name, value in entries.items():
            if not isinstance(name, str) or not isinstance(value, str):
                raise RelmError("bad_table", f"{name}: entries must map a name to an IRELM string")
            is_close = name.startswith("/")
            base = name[1:] if is_close else name
            if not _is_macro_name(base):
                raise RelmError("bad_table", f'"{name}" is not a valid macro name')
            commands = _parse_entry(base, value, is_close)
            if is_close:
                closes[base] = commands
            else:
                self.macros[base] = Macro(base, commands)
        for base, commands in closes.items():
            if base not in self.macros:
                raise RelmError("bad_table", f"/{base} has no {base} entry")
            self.macros[base].close = commands

    @classmethod
    def parse(cls, text: str) -> "Table":
        try:
            entries = yaml.load(text, Loader=_Loader)
        except yaml.YAMLError as e:
            raise RelmError("bad_table", f"not valid YAML: {e}") from None
        if entries is None:
            entries = {}
        if not isinstance(entries, dict):
            raise RelmError("bad_table", "the table must be a YAML mapping of name: IRELM")
        return cls(entries)

    @classmethod
    def load(cls, path) -> "Table":
        with open(path, encoding="utf-8") as f:
            return cls.parse(f.read())

    def names(self) -> list:
        """The named expressions, for telling the LLM what it can use."""
        return list(self.macros)

    def lookup(self, name: str, strict: bool):
        """Exact match, or in best effort mode the first case-insensitive match."""
        macro = self.macros.get(name)
        if macro or strict:
            return macro
        lower = name.lower()
        return next((m for n, m in self.macros.items() if n.lower() == lower), None)
