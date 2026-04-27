#!/bin/bash

APP_NAME="app.py"
LOG_FILE="app.log"
PID_FILE="app.pid"
BRANCH="temp1"

echo "🔄 Starting deployment..."

# -----------------------------------
# 🛑 Stop everything safely
# -----------------------------------
echo "🛑 Stopping existing processes..."

# Kill using PID file
if [ -f "$PID_FILE" ]; then
    PID=$(cat $PID_FILE)

    if ps -p $PID > /dev/null 2>&1; then
        echo "🔪 Killing PID: $PID"
        kill $PID
        sleep 2
    fi

    rm -f $PID_FILE
fi

# Kill any stray processes
EXTRA_PID=$(pgrep -f $APP_NAME)
if [ ! -z "$EXTRA_PID" ]; then
    echo "🧹 Cleaning stray processes: $EXTRA_PID"
    kill -9 $EXTRA_PID
    sleep 1
fi

# -----------------------------------
# 📥 Sync code (NO MERGE EVER)
# -----------------------------------
echo "📥 Syncing code from GitHub..."

git fetch origin $BRANCH

LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/$BRANCH)

if [ "$LOCAL" != "$REMOTE" ]; then
    echo "⚡ Updating code..."
    git reset --hard origin/$BRANCH
    git clean -fd
else
    echo "✅ Already up to date"
fi

# -----------------------------------
# 🚀 Start app (stable mode)
# -----------------------------------
echo "🚀 Starting app..."

nohup python3 $APP_NAME > $LOG_FILE 2>&1 &

NEW_PID=$!
echo $NEW_PID > $PID_FILE

sleep 2

# -----------------------------------
# 🔍 Verify start
# -----------------------------------
if ps -p $NEW_PID > /dev/null 2>&1; then
    echo "✅ App started successfully"
    echo "📌 PID: $NEW_PID"

    # -----------------------------------
    # 🔐 Ensure scripts are executable
    # -----------------------------------
    chmod +x start_app.sh stop_app.sh 2>/dev/null

    echo "🔧 Permissions updated for start/stop scripts"

else
    echo "❌ App failed to start"
    tail -n 20 $LOG_FILE
    exit 1
fi

echo "[$(date)] Deploy completed with PID $NEW_PID" >> $LOG_FILE