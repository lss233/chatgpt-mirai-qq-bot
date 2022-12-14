#!/bin/bash

xpra start :99 --no-daemon >/dev/null

export DISPLAY=:99

cd /app
python bot.py