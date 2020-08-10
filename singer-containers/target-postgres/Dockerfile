FROM python:3.8-slim

RUN apt-get update && apt-get install -y gcc git libpq-dev libssl-dev 
RUN mkdir -p /opt/code
WORKDIR /opt/code

RUN pip install pipelinewise-target-postgres

COPY entrypoint.py .
ENTRYPOINT [ "python", "./entrypoint.py" ]
