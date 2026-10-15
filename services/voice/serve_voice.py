"""
Voice service: turns text into speech using MaryTTS with Robbie's robot voice.

This is a first cut to hear how it sounds; the message format is not decided yet.
  POST /say     body is plain text, reply is a WAV file.
                Query parameters are passed to MaryTTS and override the config,
                e.g. /say?effect_robot_parameters=amount:60.0
  GET  /health  reply is "ok".

Voice settings come from robbie_services/voice.yaml in CONFIG_DIR, resolved from
config/robbie_services/voice.yaml
by scripts/resolve_config.py. It is re-read on every request, so changes apply without
a restart.

Settings, from the environment:
  - CONFIG_DIR                   resolved config folder, default /config
  - MARYTTS_URL                  MaryTTS server, default http://marytts:59125
  - PORT                         port to listen on, default 8000
  - OTEL_SERVICE_NAME            name shown in the trace viewer
  - OTEL_EXPORTER_OTLP_ENDPOINT  where to send traces; if unset, tracing does nothing

Spans record timings and sizes only, never the spoken text.
"""
import os
import signal
import sys
import threading
import time
import urllib.parse
import urllib.request
import xml.sax.saxutils
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import yaml

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

CONFIG_PATH = os.path.join(os.environ.get("CONFIG_DIR", "/config"), "robbie_services", "voice.yaml")
MARYTTS_URL = os.environ.get("MARYTTS_URL", "http://marytts:59125")
PORT = int(os.environ.get("PORT", "8000"))


def load_settings():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def to_marytts_params(settings):
    """Turns voice.yaml settings into MaryTTS request parameters."""
    params = {
        # SSML, because plain text input has no speaking rate setting.
        "INPUT_TYPE": "SSML",
        "OUTPUT_TYPE": "AUDIO",
        "AUDIO": "WAVE_FILE",
        "LOCALE": settings["locale"],
        "VOICE": settings["voice"],
    }
    for name, effect in (settings.get("effects") or {}).items():
        params[f"effect_{name}_selected"] = "on"
        params[f"effect_{name}_parameters"] = ";".join(f"{k}:{v}" for k, v in effect.items())
    return params


def to_ssml(text, rate):
    """rate is a speed multiplier (0.8 is 80% speed); SSML wants a percentage change."""
    percent = f"{round((rate - 1) * 100):+d}%"
    return (
        '<?xml version="1.0"?>'
        '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">'
        f'<prosody rate="{percent}">{xml.sax.saxutils.escape(text)}</prosody>'
        "</speak>"
    )


def setup_tracing():
    """Returns the tracer provider, or None if no endpoint is configured."""
    if not os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"):
        return None
    provider = TracerProvider(resource=Resource.create())
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(provider)
    return provider


provider = setup_tracing()
tracer = trace.get_tracer("voice")


def synthesise(text, overrides):
    settings = load_settings()
    params = {**to_marytts_params(settings), **overrides}
    params["INPUT_TEXT"] = to_ssml(text, settings.get("rate", 1.0))
    data = urllib.parse.urlencode(params).encode()
    with urllib.request.urlopen(f"{MARYTTS_URL}/process", data, timeout=30) as resp:
        return resp.read()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.reply(200, "text/plain", b"ok")
        else:
            self.reply(404, "text/plain", b"not found")

    def do_POST(self):
        url = urllib.parse.urlsplit(self.path)
        if url.path != "/say":
            self.reply(404, "text/plain", b"not found")
            return
        length = int(self.headers.get("Content-Length", 0))
        text = self.rfile.read(length).decode("utf-8").strip()
        if not text:
            self.reply(400, "text/plain", b"no text")
            return
        overrides = dict(urllib.parse.parse_qsl(url.query))

        with tracer.start_as_current_span("say") as span:
            span.set_attribute("voice.text_chars", len(text))
            start = time.monotonic()
            try:
                wav = synthesise(text, overrides)
            except Exception as e:
                span.record_exception(e)
                span.set_status(trace.Status(trace.StatusCode.ERROR))
                self.reply(502, "text/plain", f"voice failed: {e}".encode())
                return
            span.set_attribute("voice.tts_ms", round((time.monotonic() - start) * 1000))
            span.set_attribute("voice.wav_bytes", len(wav))
        self.reply(200, "audio/wav", wav)

    def reply(self, code, content_type, body):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        # The default logs every request line; keep the output to startup and shutdown.
        pass


server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
stop = threading.Event()


def request_stop(signum, frame):
    print(f"received {signal.Signals(signum).name}, shutting down", flush=True)
    stop.set()


signal.signal(signal.SIGTERM, request_stop)
signal.signal(signal.SIGINT, request_stop)

# serve_forever runs in a thread so the main thread can call shutdown(), which
# blocks until serve_forever returns.
threading.Thread(target=server.serve_forever, daemon=True).start()
print(f"ready on port {PORT}, MaryTTS at {MARYTTS_URL}, config {CONFIG_PATH}", flush=True)
stop.wait()
server.shutdown()

if provider is not None:
    provider.shutdown()

print("clean shutdown", flush=True)
sys.exit(0)
