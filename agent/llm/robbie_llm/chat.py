"""
Chat with Robbie in the terminal (just chat). Each reply is shown as RELM, then
checked with the strict RELM parser.

Commands:
  /grammar   toggle the RELM grammar (constrained decoding), on by default
  /irelm     toggle showing the IRELM each reply converts to
  /system    show the system prompt
  /reset     forget the conversation
  /quit      leave
"""
import argparse
import os
import sys
import urllib.error

from relm.convert import Converter, Options
from relm.markup import RelmError
from relm.table import Table

from .llm import RobbieLLM, system_prompt

DIM, GREEN, RED, CYAN, NORMAL = "\033[2m", "\033[32m", "\033[31m", "\033[36m", "\033[0m"


def _args(argv):
    p = argparse.ArgumentParser(prog="robbie-chat", description="Chat with Robbie's LLM.")
    p.add_argument("--url", default=os.environ.get("LLM_URL", "http://127.0.0.1:8200"))
    p.add_argument("--table", required=True, help="the RELM table (YAML)")
    p.add_argument("--persona", required=True, help="the persona system prompt")
    p.add_argument("--grammar", help="GBNF grammar from scripts/relm_grammar.py")
    p.add_argument("--locale", default=os.environ.get("LOCALE") or "en_GB",
                   help="locale for RELM AS (default: $LOCALE, then en_GB)")
    return p.parse_args(argv)


def main(argv=None):
    args = _args(argv)
    table = Table.load(args.table)
    grammar = None
    if args.grammar:
        with open(args.grammar, encoding="utf-8") as f:
            grammar = f.read()
    llm = RobbieLLM(args.url, system_prompt(args.persona, table), grammar)
    strict = Converter(table, Options(strict=True, locale=args.locale))
    constrained, show_irelm = grammar is not None, False

    print(f"{DIM}Chatting with Robbie at {args.url}. /quit to leave, /grammar, /irelm, /system, /reset.")
    print(f"grammar: {'on' if constrained else 'off'}{NORMAL}")
    while True:
        try:
            text = input(f"{CYAN}you> {NORMAL}").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not text:
            continue
        if text == "/quit":
            return
        if text == "/grammar":
            if grammar is None:
                print(f"{DIM}no grammar loaded (--grammar){NORMAL}")
            else:
                constrained = not constrained
                print(f"{DIM}grammar: {'on' if constrained else 'off'}{NORMAL}")
            continue
        if text == "/irelm":
            show_irelm = not show_irelm
            print(f"{DIM}irelm: {'on' if show_irelm else 'off'}{NORMAL}")
            continue
        if text == "/system":
            print(DIM + llm.system + NORMAL)
            continue
        if text == "/reset":
            llm.reset()
            print(f"{DIM}conversation forgotten{NORMAL}")
            continue

        print("robbie> ", end="", flush=True)
        parts = []
        try:
            for chunk in llm.reply(text, constrained):
                parts.append(chunk)
                print(chunk, end="", flush=True)
        except urllib.error.URLError as e:
            print(f"\n{RED}cannot reach the LLM at {args.url}: {e}{NORMAL}")
            continue
        except KeyboardInterrupt:
            print(f"\n{DIM}(interrupted){NORMAL}")
            continue
        print()
        try:
            irelm = strict.convert("".join(parts))
            print(f"{GREEN}  [valid RELM]{NORMAL}")
            if show_irelm:
                print(DIM + irelm + NORMAL)
        except RelmError as e:
            print(f"{RED}  [bad RELM: {e}]{NORMAL}")


if __name__ == "__main__":
    sys.exit(main())
