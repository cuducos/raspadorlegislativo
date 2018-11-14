FROM python:3.6.7-alpine

WORKDIR /code

ADD Pipfile Pipfile
ADD Pipfile.lock Pipfile.lock

RUN apk update && \
    apk add build-base g++ gcc libffi-dev libxslt-dev openssl-dev && \
    pip install -U pip && \
    pip install -U pipenv && \
    pipenv install --system --dev

ADD scrapy.cfg scrapy.cfg
ADD raspadorlegislativo /code/raspadorlegislativo
