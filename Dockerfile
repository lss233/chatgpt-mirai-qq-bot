FROM python:3.10.13-slim-bullseye

ENV DEBIAN_FRONTEND=noninteractive

COPY ./fonts/sarasa-mono-sc-regular.ttf /usr/share/fonts/

RUN apt-get update && \
    apt install --no-install-recommends xvfb binutils build-essential qtbase5-dev wkhtmltopdf ffmpeg dbus -yq && \
    (strip --remove-section=.note.ABI-tag /usr/lib/x86_64-linux-gnu/libQt5Core.so.5 || true) && \
    apt-get clean && \
    apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false && \
    rm -rf /var/lib/apt/lists/*

RUN export DBUS_SESSION_BUS_ADDRESS=`dbus-daemon --fork --config-file=/usr/share/dbus-1/session.conf --print-address`

RUN mkdir -p /app

WORKDIR /app

COPY requirements.txt /app

RUN wget https://github.com/DarkSkyTeam/chatgpt-for-bot-webui/releases/download/v0.0.1/dist.zip -O dist.zip \
    && unzip dist.zip -d web \
    && rm dist.zip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip cache purge && \
    python -c "from pycloudflared import try_cloudflare; try_cloudflare(-1)" || true

RUN apt-get remove --purge -yq binutils

COPY . /app

EXPOSE 8080

CMD ["/bin/bash", "/app/docker/start.sh"]
