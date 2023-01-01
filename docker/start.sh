#!/bin/bash

cd /app
xpra start --no-daemon --html=on --start-child="xterm -e 'python bot.py 2>&1 | tee /tmp/log.txt'"  --exit-with-children