FROM python:3.9.16-slim-bullseye

RUN mkdir -p /app
WORKDIR /app

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt install software-properties-common apt-transport-https wget ca-certificates gnupg2 -yq && \
    wget -qO /usr/share/keyrings/xpra-2022.gpg https://xpra.org/xpra-2022.gpg  && \
    echo deb [arch=amd64,arm64 signed-by=/usr/share/keyrings/xpra-2022.gpg] https://xpra.org/ bullseye main |  tee /etc/apt/sources.list.d/xpra.list && \
    wget -O- /usr/share/keyrings/google-chrome.gpg https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor --yes -o /usr/share/keyrings/google-chrome.gpg  && \
    echo deb [arch=amd64,arm64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main | tee -a /etc/apt/sources.list.d/google-chrome.list && \
    apt-get update && \
    apt install --no-install-recommends xpra xpra-html5 xvfb xfonts-base xfonts-100dpi xfonts-75dpi libgl1-mesa-dri xauth google-chrome-stable xterm -yq && \
    apt-get clean && \
    apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app
RUN pip install -r requirements.txt

COPY . /app

CMD ["/bin/bash", "/app/docker/start.sh"]