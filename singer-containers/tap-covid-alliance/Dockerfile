FROM python:3.8-slim

RUN apt-get update && apt-get install -y gcc git libssl-dev
RUN mkdir -p /opt/code
WORKDIR /opt/code

RUN pip install tap-covid-19

COPY entrypoint.py .
ENTRYPOINT python entrypoint.py
