FROM python:3.11.2-slim-bullseye

ENV DEBIAN_FRONTEND=noninteractive

COPY ./fonts/sarasa-mono-sc-regular.ttf /usr/share/fonts/

RUN apt-get update && \
    apt install --no-install-recommends xvfb binutils build-essential qtbase5-dev wkhtmltopdf ffmpeg -yq && \
    (strip --remove-section=.note.ABI-tag /usr/lib/x86_64-linux-gnu/libQt5Core.so.5 || true) && \
    apt-get clean && \
    apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /app
WORKDIR /app

COPY requirements.txt /app
RUN pip install --no-cache-dir -r requirements.txt && pip cache purge

RUN apt-get remove --purge -yq binutils

COPY . /app

CMD ["/bin/bash", "/app/docker/start.sh"]
