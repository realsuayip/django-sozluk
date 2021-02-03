FROM python:3.8.7-buster

ENV APP_DIR=/usr/src/app
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN groupadd -g 1017 django_g && useradd django -g django_g

WORKDIR $APP_DIR

RUN apt-get update && apt-get install -y netcat gosu
RUN pip install --upgrade pip
COPY ./requirements-prod.txt .
RUN pip install -r requirements-prod.txt

COPY . .

RUN mkdir -p media static

ENTRYPOINT ["/usr/src/app/entrypoint.sh"]
