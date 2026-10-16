"""RELM (what the LLM writes) to IRELM, in stack or stateless mode."""
import math
from dataclasses import dataclass

from . import say_as
from .markup import BadTag, RelmError, Tag, decode_entities, escape_attr, escape_text, scan, strip_ws, WS
from .table import PARAMS, Command, Table

_SSML_PROSODY = {"p": "pitch", "s": "rate", "r": "range", "v": "volume"}
_SSML_SAY_AS = {"datetime": "date", "number": "cardinal", "digits": "digits",
                "characters": "characters", "unit": "unit", "currency": "currency"}


@dataclass
class Options:
    stateless: bool = False
    strict: bool = False
    locale: str = "en_GB"
    prosody_to_ssml: bool = False
    voice_to_ssml: bool = False
    pause_to_ssml: bool = False
    message_to_ssml: bool = False
    audio_to_ssml: bool = False
    as_to_ssml: bool = False

    def check(self):
        spans = [f for f in ("prosody_to_ssml", "voice_to_ssml", "as_to_ssml") if getattr(self, f)]
        if self.stateless and spans:
            raise RelmError("bad_option", f"--stateless cannot be used with --{spans[0]}, SSML spans must nest")


def _percent(multiplier: str) -> str:
    x = (float(multiplier) - 1.0) * 100.0
    n = math.floor(abs(x) + 0.5)
    return f"{'-' if x < 0 and n else '+'}{n}%"


def _tag(name: str, attrs: list, self_closing: bool) -> str:
    text = "".join(f' {k}="{escape_attr(v)}"' for k, v in attrs)
    return f"<{name}{text}{'/' if self_closing else ''}>"


class Converter:
    def __init__(self, table: Table, options: Options = None):
        self.table = table
        self.options = options or Options()
        self.options.check()

    def convert(self, relm: str) -> str:
        """Convert one LLM reply. Raises RelmError in strict mode, and for bad AS text when strict."""
        return _Run(self.table, self.options).run(relm)


class _Run:
    def __init__(self, table: Table, options: Options):
        self.table = table
        self.opt = options
        self.stack = []     # [Macro]
        self.out = []

    def run(self, relm: str) -> str:
        for item in scan(relm):
            if isinstance(item, str):
                self.text(decode_entities(item))
            elif isinstance(item, BadTag):
                if self.opt.strict:
                    raise RelmError("bad_tag", f"malformed tag {item.snippet}")
            elif item.closing:
                self.close(item)
            else:
                self.open(item)
        if self.stack and self.opt.strict:
            raise RelmError("unclosed_tag", f"<{self.stack[-1].name}> is never closed")
        while self.stack:
            self.pop()
        return "<IRELM>" + "".join(self.out) + "</IRELM>"

    # --- RELM events

    def text(self, text: str):
        as_cmd = None
        if not self.opt.as_to_ssml:
            as_cmd = next((c for m in reversed(self.stack) for c in reversed(m.spans) if c.name == "AS"), None)
        body = strip_ws(text)
        if as_cmd and body:
            locale = as_cmd.get("locale") or self.opt.locale
            try:
                expanded = say_as.expand(body, as_cmd.get("format"), locale)
                start = len(text) - len(text.lstrip(WS))
                text = text[:start] + expanded + text[start + len(body):]
            except RelmError:
                if self.opt.strict:
                    raise
        self.out.append(escape_text(text))

    def open(self, tag: Tag):
        macro = self.table.lookup(tag.name, self.opt.strict)
        if macro is None:
            if self.opt.strict:
                raise RelmError("unknown_tag", f"<{tag.name}> is not in the table")
            return
        if tag.attrs and self.opt.strict:
            raise RelmError("bad_tag", f"<{tag.name}> takes no params")
        if not macro.instant:
            self.stack.append(macro)
        for cmd in macro.open:
            self.emit_open(cmd)
        if tag.self_closing and not macro.instant:
            self.pop()

    def close(self, tag: Tag):
        macro = self.table.lookup(tag.name, self.opt.strict)
        if macro is None:
            if self.opt.strict:
                raise RelmError("unknown_tag", f"</{tag.name}> is not in the table")
            return
        if macro.instant:
            return
        depth = next((i for i in range(len(self.stack) - 1, -1, -1) if self.stack[i] is macro), None)
        if depth is None:
            if self.opt.strict:
                raise RelmError("unexpected_close", f"</{tag.name}> was never opened")
            return
        if depth != len(self.stack) - 1 and self.opt.strict:
            raise RelmError("mismatched_close", f"</{tag.name}> closes before </{self.stack[-1].name}>")
        while len(self.stack) > depth:
            self.pop()

    def pop(self):
        macro = self.stack.pop()
        for cmd in reversed(macro.spans):
            self.emit_close(cmd)
        for cmd in macro.close:
            self.emit_open(cmd)

    # --- output

    def state(self, kind: str) -> str:
        values = {k: "none" for k in PARAMS[kind]}
        for macro in self.stack:
            for cmd in macro.spans:
                if cmd.name == kind:
                    for k, v in cmd.attrs:
                        if v != "none":
                            values[k] = v
        return _tag(kind, list(values.items()), True)

    def emit_open(self, cmd: Command):
        o = self.opt
        if cmd.name == "AS":
            if o.as_to_ssml:
                self.out.append(_tag("say-as", [("interpret-as", _SSML_SAY_AS[cmd.get("format")])], False))
        elif cmd.is_span and o.stateless:
            self.out.append(self.state(cmd.name))
        elif cmd.name == "PROSODY" and o.prosody_to_ssml:
            attrs = [(_SSML_PROSODY[k], _percent(v)) for k, v in cmd.attrs if v != "none"]
            self.out.append(_tag("prosody", attrs, False))
        elif cmd.name == "VOICE" and o.voice_to_ssml:
            names = {"voice": "name", "locale": "xml:lang"}
            attrs = [(names[k], v.replace("_", "-") if k == "locale" else v)
                     for k, v in cmd.attrs if v != "none"]
            self.out.append(_tag("voice", attrs, False))
        elif cmd.name == "PAUSE" and o.pause_to_ssml:
            self.out.append(_tag("break", [("time", cmd.get("duration") + "s")], True))
        elif cmd.name == "MESSAGE" and o.message_to_ssml:
            self.out.append(_tag("mark", [("name", f"{cmd.get('sub')}:{cmd.get('action')}")], True))
        elif cmd.name == "AUDIO" and o.audio_to_ssml:
            self.out.append(_tag("audio", [("src", cmd.get("file_name"))], True))
        else:
            self.out.append(cmd.xml(not cmd.is_span))

    def emit_close(self, cmd: Command):
        o = self.opt
        if cmd.name == "AS":
            if o.as_to_ssml:
                self.out.append("</say-as>")
        elif o.stateless:
            self.out.append(self.state(cmd.name))
        elif cmd.name == "PROSODY" and o.prosody_to_ssml:
            self.out.append("</prosody>")
        elif cmd.name == "VOICE" and o.voice_to_ssml:
            self.out.append("</voice>")
        else:
            self.out.append(f"</{cmd.name}>")


def convert(table: Table, relm: str, options: Options = None) -> str:
    return Converter(table, options).convert(relm)
