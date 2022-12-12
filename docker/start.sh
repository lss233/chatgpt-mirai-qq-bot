#!/bin/bash

rm /tmp/.X11-unix/X1
rm /tmp/.X1

Xvfb :99 -ac -screen 0 -nolisten tcp &
export DISPLAY=:99
cd /app
python bot.py