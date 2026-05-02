FROM timberio/vector:0.39.0-debian

RUN mkdir -p /etc/vector/lua /data/external /data/processed/collected_logs /var/lib/vector

COPY vector.toml /etc/vector/vector.toml
COPY lua/chunk_logs.lua /etc/vector/lua/chunk_logs.lua