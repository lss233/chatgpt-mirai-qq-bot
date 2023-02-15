FROM python:3.9.16-slim-bullseye

RUN mkdir -p /app
WORKDIR /app

ENV DEBIAN_FRONTEND=noninteractive

COPY requirements.txt /app
RUN pip install -r requirements.txt

COPY . /app

CMD ["/bin/bash", "/app/docker/start.sh"]