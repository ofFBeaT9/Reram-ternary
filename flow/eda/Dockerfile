# Tool image for revision 4.4 work on the PC: magic + netgen (built from source), the sky130 PDK (sky130A and
# sky130B, installed by ciel), OSS CAD Suite (yosys, nextpnr-himbaechel for Gowin, apycula, openFPGALoader).
# Build:  build_eda.bat   (docker build -t reram-eda .)
FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential git curl ca-certificates python3 python3-pip python3-venv m4 csh tcsh \
      tcl-dev tk-dev libcairo2-dev libx11-dev libxpm-dev libglu1-mesa-dev mesa-common-dev zlib1g-dev \
      libncurses-dev xz-utils ngspice && rm -rf /var/lib/apt/lists/*
# magic and netgen from their git sources (recent versions are needed by the open_pdks tech files)
RUN git clone --depth 1 https://github.com/RTimothyEdwards/magic /src/magic && cd /src/magic && \
    ./configure --prefix=/usr/local && make -j"$(nproc)" && make install && \
    git clone --depth 1 https://github.com/RTimothyEdwards/netgen /src/netgen && cd /src/netgen && \
    ./configure --prefix=/usr/local && make -j"$(nproc)" && make install && \
    (cd /src/magic && git rev-parse HEAD > /usr/local/magic.commit) && (cd /src/netgen && git rev-parse HEAD > /usr/local/netgen.commit)
# OSS CAD Suite: newest Linux x64 release
RUN URL=$(curl -s https://api.github.com/repos/YosysHQ/oss-cad-suite-build/releases/latest | \
      python3 -c "import json,sys; a=json.load(sys.stdin)['assets']; print([x['browser_download_url'] for x in a if 'linux-x64' in x['name'] and x['name'].endswith('.tgz')][0])") && \
    echo "$URL" > /opt/oss-cad-suite.url && curl -L "$URL" | tar xz -C /opt
# ciel and the sky130 PDK (both variants)
ENV PDK_ROOT=/opt/pdk
RUN python3 -m venv /opt/venv && /opt/venv/bin/pip install ciel apycula pyserial && \
    V=$(/opt/venv/bin/ciel ls-remote --pdk-family sky130 | grep -oE '[0-9a-f]{40}' | head -1) && echo "$V" > /opt/pdk.version && \
    /opt/venv/bin/ciel enable --pdk-family sky130 "$V" && ls /opt/pdk
ENV PATH=/usr/local/bin:/opt/venv/bin:/opt/oss-cad-suite/bin:$PATH
