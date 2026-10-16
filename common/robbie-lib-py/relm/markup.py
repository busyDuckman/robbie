"""Hand written tag scanner shared by the table and RELM parsers, plus XML escaping.

RELM comes from an LLM, so it is not parsed as XML: anything that does not look like a
tag is kept as text. The Rust port (robbie-lib-rs/relm/markup.rs) must behave the same.
"""
from dataclasses import dataclass, field

WS = " \t\n\r"
_ENTITIES = {"amp": "&", "lt": "<", "gt": ">", "quot": '"', "apos": "'"}


class RelmError(Exception):
    """kind is one of: bad_table, bad_tag, unknown_tag, unexpected_close,
    mismatched_close, unclosed_tag, bad_as."""

    def __init__(self, kind: str, message: str):
        super().__init__(f"{kind}: {message}")
        self.kind = kind
        self.message = message


@dataclass
class Tag:
    name: str
    attrs: list = field(default_factory=list)   # [(key, value)], values decoded
    closing: bool = False
    self_closing: bool = False


@dataclass
class BadTag:
    """A '<' that starts like a tag but is not one. The '<' itself is kept as text."""
    snippet: str


def _is_name_start(c: str) -> bool:
    return c.isascii() and (c.isalpha() or c == "_")


def _is_name_char(c: str) -> bool:
    return c.isascii() and (c.isalnum() or c in "_-.:")


def strip_ws(s: str) -> str:
    return s.strip(WS)


def _skip_ws(s: str, i: int) -> int:
    while i < len(s) and s[i] in WS:
        i += 1
    return i


def _read_name(s: str, i: int):
    if i >= len(s) or not _is_name_start(s[i]):
        return "", i
    j = i + 1
    while j < len(s) and _is_name_char(s[j]):
        j += 1
    return s[i:j], j


def _parse_tag(s: str, i: int):
    """Parse a tag starting at s[i] == '<'. Returns (Tag, end) or None."""
    n = len(s)
    j = _skip_ws(s, i + 1)
    closing = False
    if j < n and s[j] == "/":
        closing = True
        j = _skip_ws(s, j + 1)
    name, j = _read_name(s, j)
    if not name:
        return None
    attrs = []
    while True:
        k = _skip_ws(s, j)
        if k >= n:
            return None
        c = s[k]
        if c == ">":
            if closing and attrs:
                return None
            return Tag(name, attrs, closing, False), k + 1
        if c == "/":
            k2 = _skip_ws(s, k + 1)
            if k2 < n and s[k2] == ">" and not closing:
                return Tag(name, attrs, False, True), k2 + 1
            return None
        if k == j:
            return None     # attributes must be separated by whitespace
        key, k = _read_name(s, k)
        if not key:
            return None
        k = _skip_ws(s, k)
        if k >= n or s[k] != "=":
            return None
        k = _skip_ws(s, k + 1)
        if k >= n or s[k] not in "\"'":
            return None
        end = s.find(s[k], k + 1)
        if end < 0 or "<" in s[k + 1:end]:
            return None
        attrs.append((key, decode_entities(s[k + 1:end])))
        j = end + 1


def scan(s: str) -> list:
    """Split s into raw text (str, entities not yet decoded), Tag and BadTag items."""
    items, buf, i, n = [], [], 0, len(s)
    while i < n:
        if s[i] == "<":
            parsed = _parse_tag(s, i)
            if parsed:
                if buf:
                    items.append("".join(buf))
                    buf = []
                items.append(parsed[0])
                i = parsed[1]
                continue
            if i + 1 < n and (_is_name_start(s[i + 1]) or s[i + 1] == "/"):
                if buf:
                    items.append("".join(buf))
                    buf = []
                items.append(BadTag(s[i:i + 20]))
        buf.append(s[i])
        i += 1
    if buf:
        items.append("".join(buf))
    return items


def _codepoint(ent: str):
    if ent.startswith("#x") or ent.startswith("#X"):
        digits, base, ok = ent[2:], 16, "0123456789abcdefABCDEF"
    elif ent.startswith("#"):
        digits, base, ok = ent[1:], 10, "0123456789"
    else:
        return None
    if not digits or len(digits) > 8 or any(c not in ok for c in digits):
        return None
    cp = int(digits, base)
    if cp == 0 or cp > 0x10FFFF or 0xD800 <= cp <= 0xDFFF:
        return None
    return chr(cp)


def decode_entities(s: str) -> str:
    """Decode the five XML entities and numeric character references. Anything else stays."""
    out, i, n = [], 0, len(s)
    while i < n:
        if s[i] == "&":
            j = s.find(";", i + 1)
            if 0 < j - i <= 12:
                ent = s[i + 1:j]
                ch = _ENTITIES.get(ent) or _codepoint(ent)
                if ch:
                    out.append(ch)
                    i = j + 1
                    continue
        out.append(s[i])
        i += 1
    return "".join(out)


def escape_text(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def escape_attr(s: str) -> str:
    return escape_text(s).replace('"', "&quot;")


def is_number(s: str) -> bool:
    """[+-]? then digits with an optional fraction. No exponents, inf or nan."""
    if s[:1] in ("+", "-"):
        s = s[1:]
    whole, _, frac = s.partition(".")
    if not whole and not frac:
        return False
    return all(c in "0123456789" for c in whole + frac)
