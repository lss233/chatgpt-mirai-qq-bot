#!/bin/bash

xpra start :99 --no-daemon --html=on &
echo "Waiting for xpra to start"
export DISPLAY=:99
sleep 10
cd /app
python bot.py