FROM alpine:3.24

# just must be 1.43 or newer: older versions don't forward SIGTERM to the service,
# so it never shuts down cleanly (tested: 1.26 and 1.40 fail, 1.43.1 and later work).
RUN apk add --no-cache just python3

WORKDIR /service
COPY requirements.txt ./
RUN python3 -m venv /venv && /venv/bin/pip install --no-cache-dir -r requirements.txt
ENV PATH="/venv/bin:$PATH"

COPY justfile serve_voice.py ./

ENTRYPOINT ["just"]
CMD ["serve"]
