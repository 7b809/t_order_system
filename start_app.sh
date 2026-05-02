#!/bin/bash

APP_NAME="./logs/app.py"
LOG_DIR="./logs"
LOG_FILE="$LOG_DIR/app.log"
PID_FILE="$LOG_DIR/app.pid"
BRANCH="ws-order-feed"

echo "🔄 Starting deployment..."

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
    send_telegram_file("$LOG_FILE", caption="🚀 PRE-RESTART LOGS")
except Exception as e:
    print("Telegram send failed:", e)
EOF

    sleep 2
else
    echo "⚠️ No log file found to send"
fi


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

# Kill stray processes safely
PIDS=$(pgrep -f "$APP_NAME")
if [ ! -z "$PIDS" ]; then
    echo "🧹 Cleaning stray processes: $PIDS"
    echo "$PIDS" | xargs -r kill -9
    sleep 1
fi


# -----------------------------------
# 🗂 Rotate log AFTER sending
# -----------------------------------
if [ -f "$LOG_FILE" ]; then
    TS=$(date +"%Y-%m-%d_%H-%M-%S")
    mv "$LOG_FILE" "$LOG_DIR/logs_$TS.log"
    echo "🗂 Log rotated → $LOG_DIR/logs_$TS.log"
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

    # -----------------------------------
    # 📦 Install / Update dependencies
    # -----------------------------------
    if [ -f "requirements.txt" ]; then
        echo "📦 Installing dependencies..."

        # Use virtualenv if exists
        if [ -d "venv" ]; then
            echo "🐍 Using existing virtualenv"
            source venv/bin/activate
            pip install -r requirements.txt --no-cache-dir
        else
            echo "⚠️ No venv found, installing globally"
            pip3 install -r requirements.txt --no-cache-dir
        fi
    else
        echo "⚠️ requirements.txt not found, skipping dependency install"
    fi

else
    echo "✅ Already up to date"
fi


# -----------------------------------
# 🚀 Start app (stable mode)
# -----------------------------------
echo "🚀 Starting app..."

# Choose python interpreter
PYTHON_CMD="python3"
if [ -f "venv/bin/python" ]; then
    PYTHON_CMD="venv/bin/python"
fi

nohup $PYTHON_CMD $APP_NAME > $LOG_FILE 2>&1 &

NEW_PID=$!
echo $NEW_PID > $PID_FILE

sleep 2


# -----------------------------------
# 🔍 Verify start
# -----------------------------------
if ps -p $NEW_PID > /dev/null 2>&1; then
    echo "✅ App started successfully"
    echo "📌 PID: $NEW_PID"

    chmod +x start_app.sh stop_app.sh 2>/dev/null
    echo "🔧 Permissions updated for start/stop scripts"

else
    echo "❌ App failed to start"
    tail -n 20 $LOG_FILE
    exit 1
fi


echo "[$(date)] Deploy completed with PID $NEW_PID" >> $LOG_FILE