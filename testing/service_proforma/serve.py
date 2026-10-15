"""
Minimal service used to check the container lifecycle: it starts, reports ready,
and shuts down cleanly when the container is stopped.

Telemetry uses OpenTelemetry, configured by the standard environment variables:
  - OTEL_SERVICE_NAME            name shown in the trace viewer
  - OTEL_EXPORTER_OTLP_ENDPOINT  where to send traces, e.g. http://phoenix:6006
If no endpoint is set, tracing does nothing and the service runs without a viewer.

Spans record timings and attributes only, never conversation content.
"""
import os
import signal
import sys
import time

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

HEARTBEAT_INTERVAL_S = 5.0


def setup_tracing():
    """Returns the tracer provider, or None if no endpoint is configured."""
    if not os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"):
        return None
    provider = TracerProvider(resource=Resource.create())
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(provider)
    return provider


stopping = False


def request_stop(signum, frame):
    global stopping
    print(f"received {signal.Signals(signum).name}, shutting down", flush=True)
    stopping = True


signal.signal(signal.SIGTERM, request_stop)
signal.signal(signal.SIGINT, request_stop)

provider = setup_tracing()
tracer = trace.get_tracer("service_proforma")

print("ready", flush=True)
next_heartbeat = time.monotonic()
beats = 0
while not stopping:
    if time.monotonic() >= next_heartbeat:
        with tracer.start_as_current_span("heartbeat") as span:
            beats += 1
            span.set_attribute("proforma.beat", beats)
        next_heartbeat += HEARTBEAT_INTERVAL_S
    time.sleep(0.1)

# Flush any spans still waiting to be sent, otherwise the last few seconds of traces are lost.
if provider is not None:
    provider.shutdown()

# A real service would flush state here (memory store, audit log).
#   - Note: particular/scripts/tests/check_lifecycle.sh checks for this exact output, using this proforma as a test.
#           Files based on this proforma don't need to adhere.
print("clean shutdown", flush=True)
sys.exit(0)
