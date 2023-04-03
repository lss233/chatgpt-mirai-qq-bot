FROM python:3.11.2-slim-bullseye

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt install --no-install-recommends xvfb binutils qtbase5-dev -yq && \
    strip --remove-section=.note.ABI-tag /usr/lib/x86_64-linux-gnu/libQt5Core.so.5 && \
    apt-get clean && \
    apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /app
WORKDIR /app

COPY requirements.txt /app
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

RUN cp ./fonts/sarasa-mono-sc-regular.ttf /usr/share/fonts/

# Copy xpra config file
COPY ./docker/xpra.conf /etc/xpra/xpra.conf

# Set default xpra password
ENV XPRA_PASSWORD password

# Expose xpra HTML5 client port
EXPOSE 14500

CMD ["/bin/bash", "/app/docker/start.sh"]

RUN ln -sf /proc/1/fd/1 /tmp/log.txt
