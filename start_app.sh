#!/bin/bash

APP_ENTRY="manage.py"
RUN_CMD="runserver 0.0.0.0:8000"

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
# 🛑 Stop existing processes
# -----------------------------------
echo "🛑 Stopping existing processes..."

if [ -f "$PID_FILE" ]; then
    PID=$(cat $PID_FILE)

    if ps -p $PID > /dev/null 2>&1; then
        echo "🔪 Killing PID: $PID"
        kill $PID
        sleep 2
    fi

    rm -f $PID_FILE
fi

PIDS=$(pgrep -f "$APP_ENTRY")
if [ ! -z "$PIDS" ]; then
    echo "🧹 Cleaning stray processes: $PIDS"
    echo "$PIDS" | xargs -r kill -9
    sleep 1
fi


# -----------------------------------
# 🗂 Rotate logs
# -----------------------------------
if [ -f "$LOG_FILE" ]; then
    TS=$(date +"%Y-%m-%d_%H-%M-%S")
    mv "$LOG_FILE" "$LOG_DIR/logs_$TS.log"
fi


# -----------------------------------
# 📥 Sync code
# -----------------------------------
echo "📥 Syncing code from GitHub..."

git fetch origin $BRANCH

LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/$BRANCH)

if [ "$LOCAL" != "$REMOTE" ]; then
    echo "⚡ Updating code..."
    git reset --hard origin/$BRANCH
    git clean -fd

    if [ -f "requirements.txt" ]; then
        echo "📦 Installing dependencies..."

        if [ -d "venv" ]; then
            source venv/bin/activate
            pip install -r requirements.txt --no-cache-dir
        else
            pip3 install -r requirements.txt --no-cache-dir
        fi
    fi
else
    echo "✅ Already up to date"
fi


# -----------------------------------
# 🧱 Django migrations (IMPORTANT)
# -----------------------------------
echo "🧱 Running migrations..."

PYTHON_CMD="python3"
if [ -f "venv/bin/python" ]; then
    PYTHON_CMD="venv/bin/python"
fi

$PYTHON_CMD manage.py migrate --noinput


# -----------------------------------
# 🚀 Start Django server
# -----------------------------------
echo "🚀 Starting Django app..."

nohup $PYTHON_CMD $APP_ENTRY $RUN_CMD > $LOG_FILE 2>&1 &

NEW_PID=$!
echo $NEW_PID > $PID_FILE

sleep 3


# -----------------------------------
# 🔍 Verify start
# -----------------------------------
if ps -p $NEW_PID > /dev/null 2>&1; then
    echo "✅ Django app started successfully"
    echo "📌 PID: $NEW_PID"
else
    echo "❌ Failed to start Django app"
    tail -n 20 $LOG_FILE
    exit 1
fi


echo "[$(date)] Deploy completed with PID $NEW_PID" >> $LOG_FILE