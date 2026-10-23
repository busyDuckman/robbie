# The RELM listener (Rust). Built from common/robbie-lib-rs, see compose.yaml for the contexts.
FROM alpine:3.24 AS build
RUN apk add --no-cache rust cargo alsa-lib-dev pkgconf
# musl links statically by default, but libasound is a shared library.
ENV RUSTFLAGS="-C target-feature=-crt-static"
WORKDIR /src
COPY . .
RUN --mount=type=cache,target=/root/.cargo/registry \
    --mount=type=cache,target=/src/target \
    cargo build --release --bin listener && cp target/release/listener /listener

FROM alpine:3.24

# just must be 1.43 or newer: older versions don't forward SIGTERM to the service,
# so it never shuts down cleanly (tested: 1.26 and 1.40 fail, 1.43.1 and later work).
# alsa-plugins-pulse lets ALSA play through a PulseAudio socket (WSLg, a desktop).
RUN apk add --no-cache just alsa-lib alsa-plugins-pulse libgcc

WORKDIR /service
COPY --from=build /listener /usr/local/bin/listener
COPY --from=service justfile asound_pulse.conf ./

ENTRYPOINT ["just"]
CMD ["serve"]
