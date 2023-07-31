FROM python:3.11.2-slim-bullseye as builder

ENV DEBIAN_FRONTEND=noninteractive

COPY ./fonts/sarasa-mono-sc-regular.ttf /usr/share/fonts/

RUN apt-get update && \
    apt install --no-install-recommends xvfb binutils build-essential qtbase5-dev wkhtmltopdf ffmpeg -yq && \
    (strip --remove-section=.note.ABI-tag /usr/lib/x86_64-linux-gnu/libQt5Core.so.5 || true)

WORKDIR /app

COPY requirements.txt /app
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11.2-slim-bullseye

COPY --from=builder /usr/share/fonts/sarasa-mono-sc-regular.ttf /usr/share/fonts/
COPY --from=builder /usr/lib/x86_64-linux-gnu/libQt5Core.so.5 /usr/lib/x86_64-linux-gnu/
COPY --from=builder /app /app

RUN apt-get remove --purge -yq binutils && \
    apt-get clean && \
    apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false && \
    rm -rf /var/lib/apt/lists/* && \
    pip cache purge

WORKDIR /app

COPY . /app

CMD ["/bin/bash", "/app/docker/start.sh"]


