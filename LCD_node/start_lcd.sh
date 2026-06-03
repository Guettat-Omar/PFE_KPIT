#!/bin/bash
python3 /home/rasp2/LCD_node/main.py &
echo "Waiting for HTTP server..."
until curl -s http://localhost:8080/automotive_dashboard.html > /dev/null 2>&1; do
    sleep 0.5
done
echo "HTTP server ready. Starting dashboard..."
export DISPLAY=:0
chromium-browser --kiosk --noerrdialogs --disable-infobars --disable-gpu \
  --app=http://localhost:8080/automotive_dashboard.html
