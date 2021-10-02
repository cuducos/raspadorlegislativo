FROM python:3.9-slim

ENV APT_PACKAGES="gcc g++ libffi-dev libssl-dev libxslt-dev python3-dev"
WORKDIR /code

ADD Pipfile Pipfile
ADD Pipfile.lock Pipfile.lock

RUN apt-get update && \
    apt-get install -y ${APT_PACKAGES} && \
    pip install pipenv && \
    pipenv install --system --dev && \
    apt-get purge -y ${APT_PACKAGES} && \
    rm -rf /var/lib/apt/lists/*

ADD scrapy.cfg scrapy.cfg
ADD raspadorlegislativo /code/raspadorlegislativo
