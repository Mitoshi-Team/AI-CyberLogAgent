FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        coreutils \
        curl \
        git \
        gnupg \
        golang-go \
        iproute2 \
        lsb-release \
        netcat-openbsd \
        procps \
        python3 \
        python3-pip \
        python3-venv \
        python3-yaml \
        software-properties-common \
        tar \
        unzip \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN go install github.com/mingrammer/flog@latest

ENV PATH="/root/go/bin:${PATH}"

RUN git clone --depth 1 https://github.com/redcanaryco/atomic-red-team.git /opt/atomic-red-team

WORKDIR /app

COPY generator.py /app/generator.py

RUN chmod +x /app/generator.py

ENTRYPOINT ["python3", "/app/generator.py"]