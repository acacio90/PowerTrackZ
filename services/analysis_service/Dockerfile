FROM debian:bookworm-slim AS builder

WORKDIR /src

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libcjson-dev \
    libcurl4-openssl-dev \
    && rm -rf /var/lib/apt/lists/*

COPY app/main.c ./app/main.c
COPY src/analysis_service.c ./src/analysis_service.c
COPY src/analysis_service.h ./src/analysis_service.h
COPY src/strategies/backtracking.c ./src/strategies/backtracking.c
COPY src/strategies/backtracking.h ./src/strategies/backtracking.h

RUN gcc -O2 -pthread -Wall -Wextra -std=c11 app/main.c src/analysis_service.c src/strategies/backtracking.c -o analysis_service \
    -lcjson -lcurl -lm

FROM debian:bookworm-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libcjson1 \
    libcurl4 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /src/analysis_service /usr/local/bin/analysis_service

ENV PORT=5002
ENV HOST=0.0.0.0

EXPOSE 5002

HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5002/health || exit 1

CMD ["analysis_service"]
