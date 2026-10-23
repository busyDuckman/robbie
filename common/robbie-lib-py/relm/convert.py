"""RELM (what the LLM writes) to IRELM, in stack or stateless mode."""
import itertools
from dataclasses import dataclass

from . import say_as
from .markup import BadTag, RelmError, Tag, decode_entities, escape_attr, escape_text, scan, strip_ws, WS
from .table import PARAMS, Command, Table

@dataclass
class Options:
    stateless: bool = False
    strict: bool = False
    locale: str = "en_GB"


def _tag(name: str, attrs: list, self_closing: bool) -> str:
    text = "".join(f' {k}="{escape_attr(v)}"' for k, v in attrs)
    return f"<{name}{text}{'/' if self_closing else ''}>"


class Converter:
    def __init__(self, table: Table, options: Options = None):
        self.table = table
        self.options = options or Options()
        self._ids = itertools.count(1)     # MESSAGE ids, unique for the life of the converter

    def next_id(self) -> int:
        return next(self._ids)

    def convert(self, relm: str) -> str:
        """Convert one LLM reply. Raises RelmError in strict mode, and for bad AS text when strict."""
        return _Run(self.table, self.options, self.next_id).run(relm)


class _Open:
    """A macro on the stack, with the ids its messages were sent with."""
    def __init__(self, macro, ids):
        self.macro = macro
        self.ids = ids


class _Run:
    def __init__(self, table: Table, options: Options, next_id):
        self.table = table
        self.opt = options
        self.next_id = next_id
        self.stack = []     # [_Open]
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
            raise RelmError("unclosed_tag", f"<{self.stack[-1].macro.name}> is never closed")
        while self.stack:
            self.pop()
        if self.opt.stateless:
            return "".join(self.out)
        return "<IRELM>" + "".join(self.out) + "</IRELM>"

    # --- RELM events

    def text(self, text: str):
        as_cmd = next((c for o in reversed(self.stack) for c in reversed(o.macro.spans) if c.name == "AS"), None)
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
        # A macro with a "/name" entry gives each MESSAGE an id, its closes reuse them in order.
        ids = [self.next_id() for c in macro.open if c.name == "MESSAGE"] if macro.paired else []
        if not macro.instant:
            self.stack.append(_Open(macro, ids))
        sent = iter(ids)
        for cmd in macro.open:
            self.emit_open(cmd, sent)
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
        depth = next((i for i in range(len(self.stack) - 1, -1, -1) if self.stack[i].macro is macro), None)
        if depth is None:
            if self.opt.strict:
                raise RelmError("unexpected_close", f"</{tag.name}> was never opened")
            return
        if depth != len(self.stack) - 1 and self.opt.strict:
            raise RelmError("mismatched_close", f"</{tag.name}> closes before </{self.stack[-1].macro.name}>")
        while len(self.stack) > depth:
            self.pop()

    def pop(self):
        top = self.stack.pop()
        for cmd in reversed(top.macro.spans):
            self.emit_close(cmd)
        ids = iter(top.ids)
        for cmd in top.macro.close:
            self.emit_open(cmd, ids, closing=True)

    # --- output

    def state(self, kind: str) -> str:
        values = {k: "none" for k in PARAMS[kind]}
        for entry in self.stack:
            for cmd in entry.macro.spans:
                if cmd.name == kind:
                    for k, v in cmd.attrs:
                        if v != "none":
                            values[k] = v
        return _tag(kind, list(values.items()), True)

    def emit_open(self, cmd: Command, ids=None, closing: bool = False):
        """ids: the ids for this macro's messages, taken in order (none if it has no "/name")."""
        if cmd.name == "AS":
            return      # expanded here, never sent
        if cmd.is_span and self.opt.stateless:
            self.out.append(self.state(cmd.name))
            return
        extra = ()
        if cmd.name == "MESSAGE":
            msg_id = next(ids, None) if ids else None
            if msg_id is not None:
                extra = (("id", str(msg_id)),) + ((("close", "true"),) if closing else ())
        self.out.append(cmd.xml(not cmd.is_span, extra))

    def emit_close(self, cmd: Command):
        if cmd.name == "AS":
            return
        if self.opt.stateless:
            self.out.append(self.state(cmd.name))
        else:
            self.out.append(f"</{cmd.name}>")


def convert(table: Table, relm: str, options: Options = None) -> str:
    return Converter(table, options).convert(relm)
