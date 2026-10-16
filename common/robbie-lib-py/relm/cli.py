"""relm: RELM on stdin (or over HTTP) to IRELM. The Rust port is robbie-lib-rs/bin/relm.rs."""
import argparse
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .convert import Converter, Options
from .markup import RelmError
from .table import Table


def _args(argv):
    p = argparse.ArgumentParser(prog="relm", description="Convert RELM (LLM output) to IRELM.")
    p.add_argument("--table", required=True, help="the RELM to IRELM table (YAML)")
    p.add_argument("--strict", action="store_true", help="refuse bad RELM, otherwise best effort")
    p.add_argument("--stateless", action="store_true", help="emit IRELM without nesting")
    p.add_argument("--interactive", action="store_true", help="one RELM message per stdin line")
    p.add_argument("--locale", help="locale for AS (default: $LOCALE, then en_GB)")
    p.add_argument("--serve", type=int, metavar="PORT", help="serve POST / on 127.0.0.1:PORT")
    return p.parse_args(argv)


def _serve(converter: Converter, port: int):
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            if self.path != "/":
                self.send_error(404)
                return
            body = self.rfile.read(int(self.headers.get("Content-Length") or 0)).decode("utf-8")
            try:
                status, reply, kind = 200, converter.convert(body), "application/xml"
            except RelmError as e:
                status, reply, kind = 400, str(e), "text/plain"
            data = reply.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", kind + "; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"relm: serving on http://127.0.0.1:{port}/", file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


def main(argv=None):
    args = _args(argv)
    try:
        options = Options(stateless=args.stateless, strict=args.strict,
                          locale=args.locale or os.environ.get("LOCALE") or "en_GB")
        converter = Converter(Table.load(args.table), options)
        if args.serve is not None:
            _serve(converter, args.serve)
        elif args.interactive:
            for line in sys.stdin:
                try:
                    print(converter.convert(line.rstrip("\r\n")), flush=True)
                except RelmError as e:
                    print(f"relm: {e}", file=sys.stderr, flush=True)
        else:
            print(converter.convert(sys.stdin.read()))
    except (RelmError, OSError) as e:
        sys.exit(f"relm: {e}")


if __name__ == "__main__":
    main()
