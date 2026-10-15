"""
Minimal service used to check the container lifecycle: it starts, reports ready,
and shuts down cleanly when the container is stopped.
"""
import signal
import sys
import time

stopping = False


def request_stop(signum, frame):
    global stopping
    print(f"received {signal.Signals(signum).name}, shutting down", flush=True)
    stopping = True


signal.signal(signal.SIGTERM, request_stop)
signal.signal(signal.SIGINT, request_stop)

print("ready", flush=True)
while not stopping:
    time.sleep(0.1)

# A real service would flush state here (memory store, audit log).
#   - Note: particular/scripts/tests/check_lifecycle.sh checks for this exact output, using this proforma as a test.
#           Files based on this proforma don't need to adhere.
print("clean shutdown", flush=True)
sys.exit(0)
