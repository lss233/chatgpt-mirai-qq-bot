FROM python:3.11.2-slim-bullseye as builder

ENV DEBIAN_FRONTEND=noninteractive

COPY ./fonts/sarasa-mono-sc-regular.ttf /usr/share/fonts/

RUN apt-get update && \
    apt install --no-install-recommends xvfb binutils build-essential qtbase5-dev wkhtmltopdf ffmpeg -yq && \
    (strip --remove-section=.note.ABI-tag /usr/lib/x86_64-linux-gnu/libQt5Core.so.5 || true)

RUN mkdir -p /app
WORKDIR /app

COPY requirements.txt /app
RUN pip install --no-cache-dir -r requirements.txt && pip cache purge

FROM python:3.11.2-slim-bullseye

ENV DEBIAN_FRONTEND=noninteractive

COPY --from=builder /usr/share/fonts/ /usr/share/fonts/
COPY --from=builder /usr/lib/x86_64-linux-gnu/libQt5Core.so.5 /usr/lib/x86_64-linux-gnu/libQt5Core.so.5
COPY --from=builder /usr/bin/wkhtmltopdf /usr/bin/wkhtmltopdf
COPY --from=builder /usr/bin/ffmpeg /usr/bin/ffmpeg
COPY --from=builder /usr/local/lib/python3.11/site-packages/ /usr/local/lib/python3.11/site-packages/

RUN apt-get update && \
    apt install --no-install-recommends xvfb -yq && \
    apt-get remove --purge -yq binutils build-essential qtbase5-dev && \
    apt-get clean && \
    apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /app
WORKDIR /app

COPY . /app

CMD ["/bin/bash", "/app/docker/start.sh"]
