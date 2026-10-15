#!/usr/bin/env bash
# Check the service container pattern stops cleanly when Docker sends SIGTERM,
# using testing/service_proforma as the test subject. It relies on the "ready" and
# "clean shutdown" lines the proforma prints; real services don't need to print them.
# Runs twice: plain, and with --init. A failed stop shows as exit code 137 after the timeout.
# Exit code 137 means Docker had to kill the container.
#
# Usage: check_lifecycle.sh <proforma dir>
set -uo pipefail

dir="$1"
image="robbie-lifecycle-$(basename "$dir")"
docker build -q -t "$image" "$dir" > /dev/null || exit 1

failed=0
for init in "" "--init"; do
    mode="${init:-no init}"
    id=$(docker run -d $init "$image")
    for i in $(seq 50); do docker logs "$id" 2>&1 | grep -q '^ready' && break; sleep 0.2; done
    start=$(date +%s)
    docker stop -t 10 "$id" > /dev/null
    took=$(( $(date +%s) - start ))
    code=$(docker inspect -f '{{.State.ExitCode}}' "$id")
    # just exits with 143 (terminated by SIGTERM) after the service shuts down cleanly, so accept 0 or 143.
    if { [ "$code" = "0" ] || [ "$code" = "143" ]; } && docker logs "$id" 2>&1 | grep -q 'clean shutdown'; then
        echo "PASS ($mode): stopped cleanly in ${took}s (exit code $code)"
    else
        echo "FAIL ($mode): exit code $code after ${took}s"
        failed=1
    fi
    docker rm -f "$id" > /dev/null
done
exit $failed
