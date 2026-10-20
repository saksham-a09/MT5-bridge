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
        wine \
        wine64 \
        wine32 \
        xvfb \
        wget \
        curl \
        cabextract \
        procps \
        ca-certificates && \
    ( [ -f /usr/bin/wineboot ] || ln -sf /usr/lib/wine/wineboot /usr/bin/wineboot ) && \
    ( [ -f /usr/bin/wineserver ] || ln -sf /usr/lib/wine/wineserver /usr/bin/wineserver ) && \
    rm -rf /var/lib/apt/lists/*

# 2. Initialize Wine prefix and install Windows 64-bit Python 3.11
RUN Xvfb :99 -screen 0 1024x768x16 -nolisten tcp & \
    XVFB_PID=$! && \
    sleep 2 && \
    wineboot --init && wineserver -w && \
    wine reg add 'HKCU\Software\Wine' /v Version /t REG_SZ /d win10 /f && wineserver -w && \
    wget -q https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe -O /tmp/python-installer.exe && \
    wine /tmp/python-installer.exe /quiet InstallAllUsers=1 PrependPath=1 Include_pip=1 && \
    wineserver -w && \
    rm -f /tmp/python-installer.exe && \
    kill $XVFB_PID

# 3. Copy worker requirements and install into Wine Python
COPY requirements.txt .
RUN Xvfb :99 -screen 0 1024x768x16 -nolisten tcp & \
    XVFB_PID=$! && \
    sleep 2 && \
    wine python -m pip install --no-cache-dir --upgrade pip && \
    wine python -m pip install --no-cache-dir -r requirements.txt && \
    wineserver -w && \
    kill $XVFB_PID

# 4. Copy worker application code
COPY . .

# Ensure scripts and directories are ready
RUN chmod +x entrypoint.sh && mkdir -p /app/CLIENTS

ENTRYPOINT ["/app/entrypoint.sh"]
