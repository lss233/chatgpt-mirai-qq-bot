#!/bin/bash
cd /app

# Copy default data
# check if data directory exists
if [ ! -d "/app/data" ]; then
    echo "Data directory does not exist, creating..."
    mkdir /app/data
fi

# check if data directory empty
if [ -z "$(ls -A /app/data)" ]; then
    echo "Data directory is empty, copying default data..."
    cp -r /tmp/data/* /app/data
fi

# create default config
if [ ! -f "/app/data/config.yaml" ]; then
    echo "Config file does not exist, creating..."
    # 必须配置 web，否则无法访问
    cat <<EOF > /app/data/config.yaml
web:
    host: 0.0.0.0
    port: 8080
EOF
fi

python -m kirara_ai