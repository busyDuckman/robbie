"""Runs the shared cases in robbie-lib-test/relm, which the Rust port runs too."""
import json
from pathlib import Path

import pytest

from relm import Converter, Options, RelmError, Table, say_as

REPO = Path(__file__).resolve().parents[3]
DATA = REPO / "common" / "robbie-lib-test" / "relm"


def _cases(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))["cases"]


def _ids(cases):
    return [c.get("name") or f'{c["format"]} {c["locale"]} {c["input"]}' for c in cases]


CONVERT = _cases("convert_cases.json")
TABLES = _cases("table_cases.json")
SAY_AS = _cases("say_as_cases.json")


@pytest.mark.parametrize("case", CONVERT, ids=_ids(CONVERT))
def test_convert(case):
    if "table_yaml" in case:
        table = Table.parse(case["table_yaml"])
    else:
        table = Table.load(DATA / case.get("table", "example_table.yaml"))
    converter = Converter(table, Options(**case.get("options", {})))
    if "inputs" in case:
        assert [converter.convert(i) for i in case["inputs"]] == case["outputs"]
    elif "error" in case:
        with pytest.raises(RelmError) as e:
            converter.convert(case["input"])
        assert e.value.kind == case["error"]
    else:
        assert converter.convert(case["input"]) == case["output"]


@pytest.mark.parametrize("case", TABLES, ids=_ids(TABLES))
def test_table(case):
    def load():
        return Table.load(REPO / case["file"]) if "file" in case else Table.parse(case["yaml"])

    if case["ok"]:
        table = load()
        if "names" in case:
            assert table.names() == case["names"]
    else:
        with pytest.raises(RelmError) as e:
            load()
        assert e.value.kind == "bad_table"


@pytest.mark.parametrize("case", SAY_AS, ids=_ids(SAY_AS))
def test_say_as(case):
    if "error" in case:
        with pytest.raises(RelmError) as e:
            say_as(case["input"], case["format"], case["locale"])
        assert e.value.kind == case["error"]
    else:
        assert say_as(case["input"], case["format"], case["locale"]) == case["output"]
