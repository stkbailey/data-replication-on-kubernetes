# Set up the container dependencies
FROM python:3.8-slim
RUN apt-get update && apt-get install -y gcc git libpq-dev libssl-dev 

# Install a singer-container helper library
RUN pip install https://github.com/immuta/singer-container-utils/archive/master.zip

# Install the tap
RUN pip install tap-exchangeratesapi

# Set /opt/code as the default directory and copy entrypoint script
RUN mkdir -p /opt/code
WORKDIR /opt/code
COPY entrypoint.py .

# Run the entrypoint file on container start
ENTRYPOINT [ "python", "./entrypoint.py" ]
