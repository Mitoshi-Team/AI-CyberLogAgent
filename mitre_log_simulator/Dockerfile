FROM ubuntu:latest

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    bash \
    ca-certificates \
    coreutils \
    curl \
    netcat-openbsd \
    tar \
    bsdutils \
    util-linux \
    sed \
    gawk \
    procps \
    gzip \
  && rm -rf /var/lib/apt/lists/*

# Install flog binary for background noise generation.
RUN set -eux; \
    FLOGBIN_VERSION="0.4.3"; \
    curl -fsSL -o /tmp/flog.tar.gz "https://github.com/mingrammer/flog/releases/download/v${FLOGBIN_VERSION}/flog_${FLOGBIN_VERSION}_linux_amd64.tar.gz"; \
    tar -xzf /tmp/flog.tar.gz -C /tmp; \
    install -m 0755 /tmp/flog /usr/local/bin/flog; \
    rm -f /tmp/flog.tar.gz /tmp/flog

COPY orchestrator.sh /orchestrator.sh
RUN sed -i 's/\r$//' /orchestrator.sh && chmod +x /orchestrator.sh

VOLUME ["/var/log/golden"]

HEALTHCHECK --interval=30s --timeout=10s --retries=3 CMD ["bash", "-ec", "[[ ! -f /tmp/unhealthy ]] || exit 1; [[ -f /tmp/orchestrator.pid ]] || exit 1; pid=$(cat /tmp/orchestrator.pid); kill -0 $pid 2>/dev/null || exit 1; [[ -f /tmp/last_stdout_ts ]] || exit 1; now=$(date +%s); last=$(cat /tmp/last_stdout_ts); (( now - last <= 60 )) || exit 1"]

ENTRYPOINT ["/orchestrator.sh"]
