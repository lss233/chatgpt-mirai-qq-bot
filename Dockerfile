FROM python:3.9.16-slim-bullseye

RUN mkdir -p /app
WORKDIR /app

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt install software-properties-common apt-transport-https wget ca-certificates gnupg2 -yq && \
    wget -qO /usr/share/keyrings/xpra-2022.gpg https://xpra.org/xpra-2022.gpg  && \
    echo deb [arch=amd64,arm64 signed-by=/usr/share/keyrings/xpra-2022.gpg] https://xpra.org/ bullseye main |  tee /etc/apt/sources.list.d/xpra.list && \
    apt-get update && \
    apt install --no-install-recommends xpra libgl1-mesa-dri -yq


RUN set -eux; \
    apt-get clean; \
    apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false; \
    rm -rf /var/lib/apt/lists/*

RUN pip install playwright && \
    playwright install

COPY requirements.txt /app
RUN pip install -r requirements.txt

COPY . /app

# Copy xpra config file
COPY ./docker/xpra.conf /etc/xpra/xpra.conf

# Set default xpra password
ENV XPRA_PASSWORD password

# Expose xpra HTML5 client port
EXPOSE 14500

CMD ["/bin/bash", "/app/docker/start.sh"]
