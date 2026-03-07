FROM ubuntu:22.04

RUN apt-get update && apt-get install -y \
    curl \
    git \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install spacecraft_sim package (extracted orbital mechanics engine)
COPY setup/ /tmp/spacecraft_sim_pkg/
RUN pip3 install /tmp/spacecraft_sim_pkg/ && rm -rf /tmp/spacecraft_sim_pkg/
