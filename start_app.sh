#!/bin/bash

APP_NAME="app.py"
LOG_FILE="app.log"
PID_FILE="app.pid"

echo "🔄 Starting restart process..."

# -----------------------------------
# 🛑 Kill existing process
# -----------------------------------
PID=$(pgrep -f $APP_NAME)

if [ ! -z "$PID" ]; then
    echo "🛑 Killing existing process: $PID"
    kill -9 $PID
    sleep 2
else
    echo "✅ No existing process found"
fi

# -----------------------------------
# 🚀 Start new process
# -----------------------------------
echo "🚀 Starting new app..."

nohup python3 $APP_NAME > $LOG_FILE 2>&1 &

NEW_PID=$!

# Save PID
echo $NEW_PID > $PID_FILE

# -----------------------------------
# 📊 Log status
# -----------------------------------
echo "✅ App started successfully"
echo "📌 PID: $NEW_PID"
echo "📄 Logs: $LOG_FILE"

# Optional: append to log
echo "[$(date)] App restarted with PID $NEW_PID" >> $LOG_FILE