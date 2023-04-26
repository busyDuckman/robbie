import socket
import time

from utils.misc import DotBar


def wait_for_port(host, port, timeout=10):
    start_time = time.time()
    while True:
        try:
            with socket.create_connection((host, port), timeout=1):
                return time.time() - start_time
        except (socket.error, ConnectionRefusedError):
            time.sleep(1)
            if time.time() - start_time >= timeout:
                raise TimeoutError(f"Timeout while waiting for {host}:{port}")

def wait_for_port_pb(host, port, timeout=10):
    start_time = time.time()
    for i in DotBar(list(range(timeout)), heading=f"  - waiting on {host}@{port}"):
        try:
            with socket.create_connection((host, port), timeout=1):
                break
        except (socket.error, ConnectionRefusedError):
            while time.time() < (start_time + i):
                time.sleep(0.05)
            if time.time() - start_time >= timeout:
                raise TimeoutError(f"Timeout while waiting for {host}:{port}")
