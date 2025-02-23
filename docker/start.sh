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
    cp -r /tmp/data /app/data
fi

python -m kirara_ai
