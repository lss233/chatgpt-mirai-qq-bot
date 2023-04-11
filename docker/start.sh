#!/bin/bash

<<<<<<< HEAD
export DISPLAY=${DISPLAY:-:0}
XVFB_WHD=${XVFB_WHD:-1280x720x24}
XVFB_SCREEN=${XVFB_SCREEN:-0}

cd /app

# Installing fonts
cp fonts/* /usr/share/fonts/

Xvfb $DISPLAY -ac -screen $XVFB_SCREEN $XVFB_WHD -nolisten tcp &

=======
cd /app
>>>>>>> upstream/master
python bot.py