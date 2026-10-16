"""AS expansion: turn "14:30", "$12.50", "15s" etc. into words a TTS reads well.

English only. A locale with region US uses US style (no "and" in numbers, month first
dates, meter/liter). Every other locale uses British style. The default currency is the
pound for GB, the euro for IE, otherwise the dollar.
"""
import re

from .markup import RelmError, WS

ONES = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
        "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen",
        "eighteen", "nineteen"]
TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
SCALES = ["", "thousand", "million", "billion", "trillion", "quadrillion"]
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]
_ORDINALS = {"one": "first", "two": "second", "three": "third", "five": "fifth",
             "eight": "eighth", "nine": "ninth", "twelve": "twelfth"}
_CURRENCIES = {"$": ("dollar", "dollars", "cent", "cents"),
               "\u00a3": ("pound", "pounds", "penny", "pence"),
               "\u20ac": ("euro", "euros", "cent", "cents")}
_UNITS = {
    "ms": ("millisecond", "milliseconds"), "s": ("second", "seconds"),
    "sec": ("second", "seconds"), "min": ("minute", "minutes"),
    "h": ("hour", "hours"), "hr": ("hour", "hours"),
    "mm": ("millimetre", "millimetres"), "cm": ("centimetre", "centimetres"),
    "m": ("metre", "metres"), "km": ("kilometre", "kilometres"),
    "mg": ("milligram", "milligrams"), "g": ("gram", "grams"), "kg": ("kilogram", "kilograms"),
    "ml": ("millilitre", "millilitres"), "mL": ("millilitre", "millilitres"),
    "l": ("litre", "litres"), "L": ("litre", "litres"),
    "%": ("percent", "percent"), "Hz": ("hertz", "hertz"), "kHz": ("kilohertz", "kilohertz"),
    "V": ("volt", "volts"), "A": ("amp", "amps"), "W": ("watt", "watts"),
    "kW": ("kilowatt", "kilowatts"), "mAh": ("milliamp hour", "milliamp hours"),
    "mph": ("mile per hour", "miles per hour"),
    "km/h": ("kilometre per hour", "kilometres per hour"),
    "kph": ("kilometre per hour", "kilometres per hour"),
    "deg": ("degree", "degrees"),
}
MAX_DIGITS = 18

_RE_NUMBER = re.compile(r"^([+-]?)([0-9]+)(?:\.([0-9]+))?$")
_RE_ORDINAL = re.compile(r"^([0-9]+)(st|nd|rd|th)$")
_RE_TIME = re.compile(r"^([0-9]{1,2}):([0-9]{2})(?::([0-9]{2}))?(?:[ \t]*([aApP])\.?[ \t]*[mM]\.?)?$")
_RE_YEAR = re.compile(r"^[0-9]{4}$")
_RE_DATE_ISO = re.compile(r"^([0-9]{4})-([0-9]{1,2})-([0-9]{1,2})$")
_RE_DATE = re.compile(r"^([0-9]{1,2})[/.-]([0-9]{1,2})[/.-]([0-9]{4}|[0-9]{2})$")
_RE_CURRENCY = re.compile(r"^([$\u00a3\u20ac]?)[ \t]*([0-9][0-9,]*)(?:\.([0-9]{1,2}))?$")
_RE_UNIT = re.compile(r"^([+-]?[0-9][0-9,]*(?:\.[0-9]+)?)[ \t]*([^ \t0-9][^ \t]*)$")


def region(locale: str) -> str:
    """"en_GB", "en-gb" and "en_GB.UTF-8" all give "gb"."""
    tag = locale.lower().replace("-", "_").split(".")[0]
    return tag.partition("_")[2]


def _under_100(n: int) -> list:
    if n < 20:
        return [ONES[n]]
    return [TENS[n // 10]] + ([ONES[n % 10]] if n % 10 else [])


def _under_1000(n: int, gb: bool) -> list:
    words, hundreds, rest = [], n // 100, n % 100
    if hundreds:
        words += [ONES[hundreds], "hundred"]
        if rest and gb:
            words.append("and")
    if rest:
        words += _under_100(rest)
    return words


def int_words(n: int, gb: bool) -> list:
    """Cardinal words for 0 <= n < 10**18."""
    if n == 0:
        return ["zero"]
    groups = []
    while n:
        groups.append(n % 1000)
        n //= 1000
    words = []
    for i in reversed(range(len(groups))):
        g = groups[i]
        if not g:
            continue
        if i == 0 and gb and len(groups) > 1 and g < 100:
            words.append("and")
        words += _under_1000(g, gb)
        if i:
            words.append(SCALES[i])
    return words


def ordinal(words: list) -> list:
    last = words[-1]
    if last in _ORDINALS:
        last = _ORDINALS[last]
    elif last.endswith("y"):
        last = last[:-1] + "ieth"
    else:
        last += "th"
    return words[:-1] + [last]


def _digit_words(digits: str) -> list:
    return [ONES[int(c)] for c in digits]


def _number(text: str, gb: bool):
    text = text.replace(",", "")
    m = _RE_ORDINAL.fullmatch(text)
    if m:
        if len(m.group(1)) > MAX_DIGITS:
            return None
        return ordinal(int_words(int(m.group(1)), gb))
    m = _RE_NUMBER.fullmatch(text)
    if not m or len(m.group(2)) > MAX_DIGITS:
        return None
    words = ["minus"] if m.group(1) == "-" else []
    words += int_words(int(m.group(2)), gb)
    if m.group(3):
        words += ["point"] + _digit_words(m.group(3))
    return words


def _digits(text: str):
    words = []
    for c in text:
        if c in "0123456789":
            words.append(ONES[int(c)])
        elif c == "+":
            words.append("plus")
        elif c not in WS and c not in "-.()/":
            return None
    return words or None


def _characters(text: str):
    words = []
    for c in text:
        if c in "0123456789":
            words.append(ONES[int(c)])
        elif c.isascii() and c.isalpha():
            words.append(c.upper())
        elif not c.isascii():
            words.append(c)
    return words or None


def _year(y: int, gb: bool) -> list:
    if y < 1000 or 2000 <= y <= 2009 or y % 1000 == 0:
        return int_words(y, gb)
    hi, lo = y // 100, y % 100
    if lo == 0:
        return _under_100(hi) + ["hundred"]
    if lo < 10:
        return _under_100(hi) + ["oh", ONES[lo]]
    return _under_100(hi) + _under_100(lo)


def _time(text: str):
    m = _RE_TIME.fullmatch(text)
    if not m:
        return None
    h, mins = int(m.group(1)), int(m.group(2))
    if mins > 59 or (m.group(3) and int(m.group(3)) > 59):
        return None
    if m.group(4):
        if not 1 <= h <= 12:
            return None
        pm = m.group(4) in "pP"
    else:
        if h > 23:
            return None
        pm = h >= 12
        h = h % 12 or 12
    words = _under_100(h)
    if mins:
        words += ["oh", ONES[mins]] if mins < 10 else _under_100(mins)
    words += ["p", "m"] if pm else ["a", "m"]
    secs = int(m.group(3)) if m.group(3) else 0
    if secs:
        words += ["and"] + _under_100(secs) + ["second" if secs == 1 else "seconds"]
    return words


def _date(text: str, us: bool, gb: bool):
    m = _RE_DATE_ISO.fullmatch(text)
    if m:
        year, month, day = m.group(1), int(m.group(2)), int(m.group(3))
    else:
        m = _RE_DATE.fullmatch(text)
        if not m:
            return None
        a, b, year = int(m.group(1)), int(m.group(2)), m.group(3)
        month, day = (a, b) if us else (b, a)
    if not (1 <= month <= 12 and 1 <= day <= 31):
        return None
    day_words = ordinal(int_words(day, gb))
    if us:
        return [MONTHS[month - 1]] + day_words + _year(int(year), gb)
    return ["the"] + day_words + ["of", MONTHS[month - 1]] + _year(int(year), gb)


def _datetime(text: str, us: bool, gb: bool):
    words = _time(text)
    if words is None and _RE_YEAR.fullmatch(text):
        words = _year(int(text), gb)
    if words is None:
        words = _date(text, us, gb)
    if words is None:
        for sep in ("T", " "):
            if sep in text:
                d, t = text.split(sep, 1)
                dw, tw = _date(d, us, gb), _time(t.strip(WS))
                if dw and tw:
                    return dw + ["at"] + tw
    return words


def _currency(text: str, reg: str, gb: bool):
    m = _RE_CURRENCY.fullmatch(text)
    if not m:
        return None
    whole = m.group(2).replace(",", "")
    if len(whole) > MAX_DIGITS:
        return None
    symbol = m.group(1) or ("\u00a3" if reg == "gb" else "\u20ac" if reg == "ie" else "$")
    one, many, one_minor, many_minor = _CURRENCIES[symbol]
    major = int(whole)
    minor = int(m.group(3).ljust(2, "0")) if m.group(3) else 0
    words = []
    if major or not minor:
        words += int_words(major, gb) + [one if major == 1 else many]
    if minor:
        words += int_words(minor, gb) + [one_minor if minor == 1 else many_minor]
    return words


def _unit(text: str, us: bool, gb: bool):
    m = _RE_UNIT.fullmatch(text)
    if not m or m.group(2) not in _UNITS:
        return None
    words = _number(m.group(1), gb)
    if words is None:
        return None
    one, many = _UNITS[m.group(2)]
    name = one if m.group(1).lstrip("+-") == "1" else many
    if us:
        name = name.replace("metre", "meter").replace("litre", "liter")
    return words + name.split(" ")


def expand(text: str, fmt: str, locale: str) -> str:
    """Expand text (already stripped of surrounding whitespace) in the given AS format.
    Raises RelmError("bad_as") when the text cannot be read that way."""
    reg = region(locale)
    us, gb = reg == "us", reg != "us"
    if fmt == "number":
        words = _number(text, gb)
    elif fmt == "digits":
        words = _digits(text)
    elif fmt == "characters":
        words = _characters(text)
    elif fmt == "datetime":
        words = _datetime(text, us, gb)
    elif fmt == "currency":
        words = _currency(text, reg, gb)
    elif fmt == "unit":
        words = _unit(text, us, gb)
    else:
        raise RelmError("bad_as", f'unknown format "{fmt}"')
    if not words:
        raise RelmError("bad_as", f'cannot read "{text}" as {fmt}')
    return " ".join(words)
