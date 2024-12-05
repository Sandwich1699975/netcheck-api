FROM python:3.9-slim
WORKDIR /app
COPY test/requirements.txt /app/test-requirements.txt
COPY src/requirements.txt /app/src-requirements.txt

RUN pip install --no-cache-dir -r test-requirements.txt && \
    pip install --no-cache-dir -r src-requirements.txt

# Install sudo and create a non-root user
RUN apt-get update && apt-get install -y sudo && \
    useradd -m -s /bin/bash nonrootuser && \
    echo "nonrootuser ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

USER nonrootuser


ENV DEBUG_MODE=true

COPY ./src /app
COPY ./test /app
COPY ./pyproject.toml /app

CMD ["sudo", "pytest", "--color=yes", "-v"]
