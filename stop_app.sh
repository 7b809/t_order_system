#!/bin/bash

APP_NAME="app.py"
LOG_FILE="app.log"
PID_FILE="app.pid"

echo "🛑 Stopping application..."

STOPPED=false

# -----------------------------------
# 📤 Send logs BEFORE stopping
# -----------------------------------
echo "📤 Sending logs to Telegram..."

if [ -f "$LOG_FILE" ]; then
    python3 - <<EOF
from utils.telegram_service import send_telegram_file
send_telegram_file("app.log", caption="🛑 Logs before STOP")
EOF
    sleep 2
else
    echo "⚠️ No log file found to send"
fi


# -----------------------------------
# 📌 Stop using PID file
# -----------------------------------
if [ -f "$PID_FILE" ]; then
    PID=$(cat $PID_FILE)

    if ps -p $PID > /dev/null 2>&1; then
        echo "🔪 Killing PID: $PID"
        kill $PID
        sleep 2
        STOPPED=true
    fi

    rm -f $PID_FILE
fi


# -----------------------------------
# 🧹 Kill stray processes (IMPORTANT)
# -----------------------------------
EXTRA_PID=$(pgrep -f $APP_NAME)

if [ ! -z "$EXTRA_PID" ]; then
    echo "🧹 Killing stray processes: $EXTRA_PID"
    kill -9 $EXTRA_PID
    sleep 1
    STOPPED=true
fi


# -----------------------------------
# 📊 Final status
# -----------------------------------
REMAINING=$(pgrep -f $APP_NAME)

if [ -z "$REMAINING" ]; then
    echo "✅ App fully stopped"
else
    echo "❌ Some processes still running: $REMAINING"
fi