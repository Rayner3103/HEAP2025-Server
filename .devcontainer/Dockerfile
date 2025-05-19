FROM mcr.microsoft.com/devcontainers/python:1-3.12-bullseye
RUN apt-get update

RUN pip install --upgrade pip
# Install production dependencies
COPY requirements.txt /tmp/requirements.txt
RUN python -m pip install -r /tmp/requirements.txt
RUN rm /tmp/requirements.txt