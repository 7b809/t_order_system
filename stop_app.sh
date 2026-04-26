#!/bin/bash

PID_FILE="app.pid"

echo "🛑 Stopping application..."

# -----------------------------------
# 📌 Check if PID file exists
# -----------------------------------
if [ ! -f "$PID_FILE" ]; then
    echo "❌ PID file not found. App may not be running."
    exit 1
fi

PID=$(cat $PID_FILE)

# -----------------------------------
# 🔍 Check if process exists
# -----------------------------------
if ps -p $PID > /dev/null 2>&1; then
    echo "🔪 Killing process with PID: $PID"
    kill -9 $PID
    sleep 1

    # Double check
    if ps -p $PID > /dev/null 2>&1; then
        echo "❌ Failed to stop process"
    else
        echo "✅ App stopped successfully"
        rm -f $PID_FILE
    fi
else
    echo "⚠️ No running process found for PID: $PID"
    rm -f $PID_FILE
fi