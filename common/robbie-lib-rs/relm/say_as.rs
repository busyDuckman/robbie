//! AS expansion: turn "14:30", "$12.50", "15s" etc. into words a TTS reads well.
//!
//! English only. A locale with region US uses US style (no "and" in numbers, month first
//! dates, meter/liter). Every other locale uses British style. The default currency is the
//! pound for GB, the euro for IE, otherwise the dollar.
//! Port of robbie-lib-py/relm/say_as.py, keep the two the same.

use std::sync::LazyLock;

use regex::Regex;

use super::markup::{strip_ws, ErrorKind, RelmError, WS};

const ONES: [&str; 20] = [
    "zero",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
    "eleven",
    "twelve",
    "thirteen",
    "fourteen",
    "fifteen",
    "sixteen",
    "seventeen",
    "eighteen",
    "nineteen",
];
const TENS: [&str; 10] = [
    "", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety",
];
const SCALES: [&str; 6] = [
    "",
    "thousand",
    "million",
    "billion",
    "trillion",
    "quadrillion",
];
const MONTHS: [&str; 12] = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
];
const MAX_DIGITS: usize = 18;

const POUND: char = '\u{a3}';
const EURO: char = '\u{20ac}';

fn currency_names(symbol: char) -> [&'static str; 4] {
    match symbol {
        POUND => ["pound", "pounds", "penny", "pence"],
        EURO => ["euro", "euros", "cent", "cents"],
        _ => ["dollar", "dollars", "cent", "cents"],
    }
}

/// A currency code: (home region, qualifier when read elsewhere, symbol for the names).
fn currency_code(code: &str) -> Option<(&'static str, &'static str, char)> {
    Some(match code {
        "USD" => ("us", "US", '$'),
        "AUD" => ("au", "Australian", '$'),
        "NZD" => ("nz", "New Zealand", '$'),
        "CAD" => ("ca", "Canadian", '$'),
        "GBP" => ("gb", "", POUND),
        "EUR" => ("", "", EURO),
        _ => return None,
    })
}

fn unit_names(unit: &str) -> Option<(&'static str, &'static str)> {
    Some(match unit {
        "ms" => ("millisecond", "milliseconds"),
        "s" | "sec" => ("second", "seconds"),
        "min" => ("minute", "minutes"),
        "h" | "hr" => ("hour", "hours"),
        "mm" => ("millimetre", "millimetres"),
        "cm" => ("centimetre", "centimetres"),
        "m" => ("metre", "metres"),
        "km" => ("kilometre", "kilometres"),
        "mg" => ("milligram", "milligrams"),
        "g" => ("gram", "grams"),
        "kg" => ("kilogram", "kilograms"),
        "ml" | "mL" => ("millilitre", "millilitres"),
        "l" | "L" => ("litre", "litres"),
        "%" => ("percent", "percent"),
        "Hz" => ("hertz", "hertz"),
        "kHz" => ("kilohertz", "kilohertz"),
        "V" => ("volt", "volts"),
        "A" => ("amp", "amps"),
        "W" => ("watt", "watts"),
        "kW" => ("kilowatt", "kilowatts"),
        "mAh" => ("milliamp hour", "milliamp hours"),
        "mph" => ("mile per hour", "miles per hour"),
        "km/h" | "kph" => ("kilometre per hour", "kilometres per hour"),
        "deg" => ("degree", "degrees"),
        _ => return None,
    })
}

fn re(pattern: &str) -> Regex {
    Regex::new(pattern).expect("valid regex")
}

static RE_NUMBER: LazyLock<Regex> = LazyLock::new(|| re(r"^([+-]?)([0-9]+)(?:\.([0-9]+))?$"));
static RE_ORDINAL: LazyLock<Regex> = LazyLock::new(|| re(r"^([0-9]+)(st|nd|rd|th)$"));
static RE_TIME: LazyLock<Regex> = LazyLock::new(|| {
    re(r"^([0-9]{1,2}):([0-9]{2})(?::([0-9]{2}))?(?:[ \t]*([aApP])\.?[ \t]*[mM]\.?)?$")
});
static RE_YEAR: LazyLock<Regex> = LazyLock::new(|| re(r"^[0-9]{4}$"));
static RE_DATE_ISO: LazyLock<Regex> =
    LazyLock::new(|| re(r"^([0-9]{4})-([0-9]{1,2})-([0-9]{1,2})$"));
static RE_DATE: LazyLock<Regex> =
    LazyLock::new(|| re(r"^([0-9]{1,2})[/.-]([0-9]{1,2})[/.-]([0-9]{4}|[0-9]{2})$"));
static RE_CURRENCY: LazyLock<Regex> = LazyLock::new(|| {
    re(
        r"^(?:([A-Z]{3})[ \t]*)?([$\x{A3}\x{20AC}]?)[ \t]*([0-9][0-9,]*)(?:\.([0-9]{1,2}))?(?:[ \t]*([A-Z]{3}))?$",
    )
});
static RE_UNIT: LazyLock<Regex> =
    LazyLock::new(|| re(r"^([+-]?[0-9][0-9,]*(?:\.[0-9]+)?)[ \t]*([^ \t0-9][^ \t]*)$"));

type Words = Vec<String>;

fn words(items: &[&str]) -> Words {
    items.iter().map(|w| w.to_string()).collect()
}

/// "en_GB", "en-gb" and "en_GB.UTF-8" all give "gb".
pub fn region(locale: &str) -> String {
    let tag = locale.to_lowercase().replace('-', "_");
    let tag = tag.split('.').next().unwrap_or("");
    tag.split_once('_')
        .map(|(_, r)| r.to_string())
        .unwrap_or_default()
}

fn under_100(n: u64) -> Words {
    let n = n as usize;
    if n < 20 {
        return words(&[ONES[n]]);
    }
    let mut w = words(&[TENS[n / 10]]);
    if !n.is_multiple_of(10) {
        w.push(ONES[n % 10].into());
    }
    w
}

fn under_1000(n: u64, gb: bool) -> Words {
    let (hundreds, rest) = (n / 100, n % 100);
    let mut w = Words::new();
    if hundreds != 0 {
        w.extend(words(&[ONES[hundreds as usize], "hundred"]));
        if rest != 0 && gb {
            w.push("and".into());
        }
    }
    if rest != 0 {
        w.extend(under_100(rest));
    }
    w
}

/// Cardinal words for n < 10**18.
pub fn int_words(mut n: u64, gb: bool) -> Words {
    if n == 0 {
        return words(&["zero"]);
    }
    let mut groups = Vec::new();
    while n != 0 {
        groups.push(n % 1000);
        n /= 1000;
    }
    let mut w = Words::new();
    for i in (0..groups.len()).rev() {
        let g = groups[i];
        if g == 0 {
            continue;
        }
        if i == 0 && gb && groups.len() > 1 && g < 100 {
            w.push("and".into());
        }
        w.extend(under_1000(g, gb));
        if i != 0 {
            w.push(SCALES[i].into());
        }
    }
    w
}

pub fn ordinal(mut w: Words) -> Words {
    let last = w.pop().unwrap_or_default();
    let last = match last.as_str() {
        "one" => "first".to_string(),
        "two" => "second".to_string(),
        "three" => "third".to_string(),
        "five" => "fifth".to_string(),
        "eight" => "eighth".to_string(),
        "nine" => "ninth".to_string(),
        "twelve" => "twelfth".to_string(),
        s if s.ends_with('y') => format!("{}ieth", &s[..s.len() - 1]),
        s => format!("{s}th"),
    };
    w.push(last);
    w
}

fn digit_words(digits: &str) -> Words {
    digits
        .chars()
        .map(|c| ONES[c.to_digit(10).unwrap_or(0) as usize].to_string())
        .collect()
}

fn parse_int(digits: &str) -> Option<u64> {
    if digits.len() > MAX_DIGITS {
        return None;
    }
    digits.parse().ok()
}

fn number(text: &str, gb: bool) -> Option<Words> {
    let text = text.replace(',', "");
    if let Some(m) = RE_ORDINAL.captures(&text) {
        return Some(ordinal(int_words(parse_int(&m[1])?, gb)));
    }
    let m = RE_NUMBER.captures(&text)?;
    let mut w = if &m[1] == "-" {
        words(&["minus"])
    } else {
        Words::new()
    };
    w.extend(int_words(parse_int(&m[2])?, gb));
    if let Some(frac) = m.get(3) {
        w.push("point".into());
        w.extend(digit_words(frac.as_str()));
    }
    Some(w)
}

fn digits(text: &str) -> Option<Words> {
    let mut w = Words::new();
    for c in text.chars() {
        if let Some(d) = c.to_digit(10).filter(|_| c.is_ascii_digit()) {
            w.push(ONES[d as usize].into());
        } else if c == '+' {
            w.push("plus".into());
        } else if !WS.contains(&c) && !"-.()/".contains(c) {
            return None;
        }
    }
    (!w.is_empty()).then_some(w)
}

fn characters(text: &str) -> Option<Words> {
    let mut w = Words::new();
    for c in text.chars() {
        if c.is_ascii_digit() {
            w.push(ONES[c.to_digit(10).unwrap_or(0) as usize].into());
        } else if c.is_ascii_alphabetic() {
            w.push(c.to_ascii_uppercase().to_string());
        } else if !c.is_ascii() {
            w.push(c.to_string());
        }
    }
    (!w.is_empty()).then_some(w)
}

fn year(y: u64, gb: bool) -> Words {
    if y < 1000 || (2000..=2009).contains(&y) || y.is_multiple_of(1000) {
        return int_words(y, gb);
    }
    let (hi, lo) = (y / 100, y % 100);
    let mut w = under_100(hi);
    if lo == 0 {
        w.push("hundred".into());
    } else if lo < 10 {
        w.extend(words(&["oh", ONES[lo as usize]]));
    } else {
        w.extend(under_100(lo));
    }
    w
}

fn time(text: &str) -> Option<Words> {
    let m = RE_TIME.captures(text)?;
    let mut h: u64 = m[1].parse().ok()?;
    let mins: u64 = m[2].parse().ok()?;
    let secs: u64 = match m.get(3) {
        Some(s) => s.as_str().parse().ok()?,
        None => 0,
    };
    if mins > 59 || secs > 59 {
        return None;
    }
    let pm = if let Some(ampm) = m.get(4) {
        if !(1..=12).contains(&h) {
            return None;
        }
        "pP".contains(ampm.as_str())
    } else {
        if h > 23 {
            return None;
        }
        let pm = h >= 12;
        h = if h.is_multiple_of(12) { 12 } else { h % 12 };
        pm
    };
    let mut w = under_100(h);
    if mins != 0 {
        if mins < 10 {
            w.extend(words(&["oh", ONES[mins as usize]]));
        } else {
            w.extend(under_100(mins));
        }
    }
    w.extend(words(if pm { &["p", "m"] } else { &["a", "m"] }));
    if secs != 0 {
        w.push("and".into());
        w.extend(under_100(secs));
        w.push(if secs == 1 { "second" } else { "seconds" }.into());
    }
    Some(w)
}

fn date(text: &str, us: bool, gb: bool) -> Option<Words> {
    let (y, month, day): (String, u64, u64) = if let Some(m) = RE_DATE_ISO.captures(text) {
        (m[1].to_string(), m[2].parse().ok()?, m[3].parse().ok()?)
    } else {
        let m = RE_DATE.captures(text)?;
        let (a, b): (u64, u64) = (m[1].parse().ok()?, m[2].parse().ok()?);
        let (month, day) = if us { (a, b) } else { (b, a) };
        (m[3].to_string(), month, day)
    };
    if !((1..=12).contains(&month) && (1..=31).contains(&day)) {
        return None;
    }
    let day_words = ordinal(int_words(day, gb));
    let year_words = year(y.parse().ok()?, gb);
    let month = MONTHS[month as usize - 1].to_string();
    let mut w = Words::new();
    if us {
        w.push(month);
        w.extend(day_words);
    } else {
        w.push("the".into());
        w.extend(day_words);
        w.push("of".into());
        w.push(month);
    }
    w.extend(year_words);
    Some(w)
}

fn datetime(text: &str, us: bool, gb: bool) -> Option<Words> {
    let mut w = time(text);
    if w.is_none() && RE_YEAR.is_match(text) {
        w = Some(year(text.parse().ok()?, gb));
    }
    if w.is_none() {
        w = date(text, us, gb);
    }
    if w.is_none() {
        for sep in ['T', ' '] {
            if let Some((d, t)) = text.split_once(sep) {
                if let (Some(mut dw), Some(tw)) = (date(d, us, gb), time(strip_ws(t))) {
                    dw.push("at".into());
                    dw.extend(tw);
                    return Some(dw);
                }
            }
        }
    }
    w
}

fn currency(text: &str, reg: &str, gb: bool) -> Option<Words> {
    let m = RE_CURRENCY.captures(text)?;
    let (code, code_after) = (m.get(1), m.get(5));
    let mut symbol = m[2].chars().next();
    if (code.is_some() && code_after.is_some())
        || (code.or(code_after).is_some() && symbol.is_some())
    {
        return None;
    }
    let whole = m[3].replace(',', "");
    let major = parse_int(&whole)?;
    let mut qualifier = Words::new();
    if let Some(code) = code.or(code_after) {
        let (home, country, sym) = currency_code(code.as_str())?;
        if !country.is_empty() && home != reg {
            qualifier = country.split(' ').map(String::from).collect();
        }
        symbol = Some(sym);
    }
    let symbol = symbol.unwrap_or(match reg {
        "gb" => POUND,
        "ie" => EURO,
        _ => '$',
    });
    let [one, many, one_minor, many_minor] = currency_names(symbol);
    let minor: u64 = match m.get(4) {
        Some(frac) => format!("{:0<2}", frac.as_str()).parse().ok()?,
        None => 0,
    };
    let mut w = Words::new();
    if major != 0 || minor == 0 {
        w.extend(int_words(major, gb));
        w.extend(qualifier);
        w.push(if major == 1 { one } else { many }.into());
    }
    if minor != 0 {
        w.extend(int_words(minor, gb));
        w.push(if minor == 1 { one_minor } else { many_minor }.into());
    }
    Some(w)
}

fn unit(text: &str, us: bool, gb: bool) -> Option<Words> {
    let m = RE_UNIT.captures(text)?;
    let (one, many) = unit_names(&m[2])?;
    let mut w = number(&m[1], gb)?;
    let mut name = if m[1].trim_start_matches(['+', '-']) == "1" {
        one
    } else {
        many
    }
    .to_string();
    if us {
        name = name.replace("metre", "meter").replace("litre", "liter");
    }
    w.extend(name.split(' ').map(String::from));
    Some(w)
}

/// Expand text (already stripped of surrounding whitespace) in the given AS format.
pub fn expand(text: &str, format: &str, locale: &str) -> Result<String, RelmError> {
    let reg = region(locale);
    let (us, gb) = (reg == "us", reg != "us");
    let w = match format {
        "number" => number(text, gb),
        "digits" => digits(text),
        "characters" => characters(text),
        "datetime" => datetime(text, us, gb),
        "currency" => currency(text, &reg, gb),
        "unit" => unit(text, us, gb),
        _ => {
            return Err(RelmError::new(
                ErrorKind::BadAs,
                format!("unknown format \"{format}\""),
            ))
        }
    };
    match w {
        Some(w) if !w.is_empty() => Ok(w.join(" ")),
        _ => Err(RelmError::new(
            ErrorKind::BadAs,
            format!("cannot read \"{text}\" as {format}"),
        )),
    }
}
