FROM python:3.9-alpine

RUN mkdir -p /app
WORKDIR /app

COPY requirements.txt /app
RUN pip install -r requirements.txt

COPY . /app

EXPOSE 8080


CMD ["python", "bot.py"]
