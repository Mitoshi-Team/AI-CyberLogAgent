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
        software-properties-common \
        tar \
        unzip \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://packages.microsoft.com/config/ubuntu/24.04/packages-microsoft-prod.deb -o /tmp/packages-microsoft-prod.deb \
    && dpkg -i /tmp/packages-microsoft-prod.deb \
    && rm -f /tmp/packages-microsoft-prod.deb \
    && apt-get update \
    && apt-get install -y --no-install-recommends powershell \
    && rm -rf /var/lib/apt/lists/*

RUN go install github.com/mingrammer/flog@latest

ENV PATH="/root/go/bin:${PATH}"

ENV PSModulePath="/opt/ps-modules:/root/.local/share/powershell/Modules:/usr/local/share/powershell/Modules:/usr/share/powershell/Modules"

RUN mkdir -p /opt/ps-modules \
    && git clone --depth 1 https://github.com/cloudbase/powershell-yaml.git /opt/ps-modules/powershell-yaml \
    && git clone --depth 1 https://github.com/redcanaryco/invoke-atomicredteam.git /opt/ps-modules/Invoke-AtomicRedTeam \
    && git clone --depth 1 https://github.com/redcanaryco/atomic-red-team.git /opt/atomic-red-team \
    && pwsh -NoLogo -NoProfile -Command "Import-Module Invoke-AtomicRedTeam -Force; Get-Command Invoke-AtomicTest | Out-Null"

WORKDIR /app

COPY generator.py /app/generator.py

RUN chmod +x /app/generator.py

ENTRYPOINT ["python3", "/app/generator.py"]