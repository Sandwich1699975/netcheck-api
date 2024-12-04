FROM python:3.9-slim
WORKDIR /app
COPY test/requirements.txt /app/test-requirements.txt
COPY src/requirements.txt /app/src-requirements.txt

RUN pip install --no-cache-dir -r test-requirements.txt && \
    pip install --no-cache-dir -r src-requirements.txt

COPY ./src /app
COPY ./test /app
COPY ./pyproject.toml /app

CMD ["pytest", "--color=yes"]