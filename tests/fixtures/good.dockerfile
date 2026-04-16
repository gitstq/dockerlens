FROM python:3.12-slim@sha256:abc123
RUN adduser --disabled-password appuser && \
    apt-get update && \
    apt-get install --no-install-recommends -y curl=7.88.1 && \
    rm -rf /var/lib/apt/lists/*
USER appuser
WORKDIR /app
COPY . /app
EXPOSE 8080
HEALTHCHECK --interval=30s CMD curl -f http://localhost:8080/health || exit 1
ENTRYPOINT ["python3", "app.py"]
CMD ["--port", "8080"]
