
FROM gcc:15.2-bookworm
RUN useradd --create-home --uid 10001 runner
USER 10001:10001
WORKDIR /work
ENTRYPOINT ["/bin/sh", "-lc"]
