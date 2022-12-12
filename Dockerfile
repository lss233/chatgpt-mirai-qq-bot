FROM python:3.9.16-slim-bullseye

RUN mkdir -p /app
WORKDIR /app

RUN apt-get update && \
    apt install software-properties-common apt-transport-https wget ca-certificates gnupg2 -yq && \
    wget -qO - https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor | tee /usr/share/keyrings/google-chrome.gpg >/dev/null && \
    echo deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main |  tee /etc/apt/sources.list.d/google-chrome.list && \
    apt-get update && \
    apt install --no-install-recommends google-chrome-stable xvfb  libgl1-mesa-dri -yq


RUN set -eux; \
    apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false; \
    rm -rf /var/lib/apt/lists/*


COPY requirements.txt /app
RUN pip install -r requirements.txt

COPY . /app

CMD ["/bin/bash", "/app/docker/start.sh"]
