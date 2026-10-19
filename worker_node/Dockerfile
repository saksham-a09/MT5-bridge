FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV WINEDEBUG=-all
ENV WINEPREFIX=/root/.wine
ENV DISPLAY=:99

WORKDIR /app

# 1. Enable 32-bit architecture & install Wine, Xvfb, and system tools
RUN dpkg --add-architecture i386 && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        wine64 \
        wine32 \
        xvfb \
        wget \
        curl \
        cabextract \
        procps \
        ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# 2. Initialize Wine prefix in headless mode
RUN wineboot --init && wineserver -w

# 3. Download and install Windows 64-bit Python 3.11 inside Wine
RUN wget -q https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe -O /tmp/python-installer.exe && \
    wine /tmp/python-installer.exe /quiet InstallAllUsers=1 PrependPath=1 && \
    wineserver -w && \
    rm /tmp/python-installer.exe

# 4. Copy worker requirements and install into Wine Python
COPY requirements.txt .
RUN wine python -m pip install --no-cache-dir --upgrade pip && \
    wine python -m pip install --no-cache-dir -r requirements.txt && \
    wineserver -w

# 5. Copy worker application code
COPY . .

# Ensure scripts and directories are ready
RUN chmod +x entrypoint.sh && mkdir -p /app/CLIENTS

ENTRYPOINT ["/app/entrypoint.sh"]
