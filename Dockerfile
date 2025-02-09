FROM python:3.10.13-slim-bullseye

ENV DEBIAN_FRONTEND=noninteractive

COPY ./data/fonts/sarasa-mono-sc-regular.ttf /usr/share/fonts/

RUN apt-get -yqq update && \
    apt-get -yqq install --no-install-recommends xvfb binutils build-essential qtbase5-dev wkhtmltopdf ffmpeg dbus curl jq unzip && \
    (strip --remove-section=.note.ABI-tag /usr/lib/x86_64-linux-gnu/libQt5Core.so.5 || true) && \
    apt-get -yq clean && \
    apt-get -yq purge --auto-remove -o APT::AutoRemove::RecommendsImportant=false && \
    rm -rf /var/lib/apt/lists/*

RUN export DBUS_SESSION_BUS_ADDRESS=`dbus-daemon --fork --config-file=/usr/share/dbus-1/session.conf --print-address`

RUN mkdir -p /app

WORKDIR /app

COPY requirements.txt /app

RUN LATEST_RELEASE_URL=$(curl -s https://api.github.com/repos/DarkSkyTeam/chatgpt-for-bot-webui/releases | jq -r '.[0].assets[] | select(.name == "dist.zip") | .browser_download_url') \
    && curl -L -o dist.zip "$LATEST_RELEASE_URL" \
    && unzip dist.zip -d web \
    && rm dist.zip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip cache purge && \
    python -c "from pycloudflared import try_cloudflare; try_cloudflare(-1)" || true

RUN apt-get -yqq remove --purge binutils unzip curl jq

COPY . /app

EXPOSE 8080

CMD ["/bin/bash", "/app/docker/start.sh"]
