FROM python:3.11.0-alpine3.15

# Speedtest CLI Version
ARG SPEEDTEST_VERSION=1.2.0

# Create user for speedtest CLI only
RUN adduser -D speedtest

WORKDIR /app
COPY src/requirements.txt .

ENV SPEEDTEST_PORT=9798

# Install required modules and Speedtest CLI
RUN pip install --no-cache-dir -r requirements.txt && \
    ARCHITECTURE=$(uname -m) && \
    export ARCHITECTURE && \
    if [ "$ARCHITECTURE" = 'armv7l' ];then ARCHITECTURE="armhf";fi && \
    wget -nv -O /tmp/speedtest.tgz "https://install.speedtest.net/app/cli/ookla-speedtest-${SPEEDTEST_VERSION}-linux-${ARCHITECTURE}.tgz" && \
    tar zxvf /tmp/speedtest.tgz -C /tmp && \
    cp /tmp/speedtest /usr/local/bin && \
    chown -R speedtest:speedtest /app && \
    rm -rf \
    /tmp/* \
    /app/requirements

COPY src/. .

# Use root user to spawn ping packets 

CMD ["python", "-u", "main.py"]

HEALTHCHECK --timeout=10s CMD wget --no-verbose --tries=1 --spider http://0.0.0.0:${SPEEDTEST_PORT}/ || exit 1
