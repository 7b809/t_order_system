#!/bin/bash

APP_NAME="./logs/app.py"
LOG_DIR="./logs"
LOG_FILE="$LOG_DIR/app.log"
PID_FILE="$LOG_DIR/app.pid"

echo "🛑 Stopping application..."

STOPPED=false

# Ensure logs directory exists
mkdir -p $LOG_DIR

# -----------------------------------
# 📤 Send logs BEFORE stopping
# -----------------------------------
echo "📤 Sending logs to Telegram..."

if [ -f "$LOG_FILE" ]; then
    python3 - <<EOF
import sys
sys.path.append(".")
try:
    from utils.telegram_service import send_telegram_file
    send_telegram_file("$LOG_FILE", caption="🛑 Logs before STOP")
except Exception as e:
    print("Telegram send failed:", e)
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
# 🧹 Kill stray processes safely
# -----------------------------------
PIDS=$(pgrep -f "$APP_NAME")

if [ ! -z "$PIDS" ]; then
    echo "🧹 Killing stray processes: $PIDS"
    echo "$PIDS" | xargs -r kill -9
    sleep 1
    STOPPED=true
fi


# -----------------------------------
# 📊 Final status
# -----------------------------------
REMAINING=$(pgrep -f "$APP_NAME")

if [ -z "$REMAINING" ]; then
    echo "✅ App fully stopped"
else
    echo "❌ Some processes still running: $REMAINING"
fi


# -----------------------------------
# 🧾 Summary
# -----------------------------------
if [ "$STOPPED" = true ]; then
    echo "📌 Stop operation completed"
else
    echo "⚠️ No running process found"
fi