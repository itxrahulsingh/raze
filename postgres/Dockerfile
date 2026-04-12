FROM postgres:16-alpine

# Install build dependencies for pgvector
RUN apk add --no-cache \
    gcc \
    g++ \
    make \
    git \
    clang15 \
    llvm15 \
    pkgconfig

# Clone and build pgvector
RUN git clone https://github.com/pgvector/pgvector.git /tmp/pgvector && \
    cd /tmp/pgvector && \
    make && \
    make install && \
    rm -rf /tmp/pgvector

# Cleanup
RUN apk del gcc g++ make git clang15 llvm15 pkgconfig && \
    rm -rf /var/cache/apk/*
