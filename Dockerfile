# syntax=docker/dockerfile:1

# Comments are provided throughout this file to help you get started.
# If you need more help, visit the Dockerfile reference guide at
# https://docs.docker.com/engine/reference/builder/

ARG PYTHON_VERSION=3.8.2
FROM python:${PYTHON_VERSION}-slim as base

COPY requirements.txt .

RUN python -m pip install -r requirements.txt

WORKDIR /whatsapp-bot

COPY . /whatsapp-bot

ENTRYPOINT ["python", "bot.py"]