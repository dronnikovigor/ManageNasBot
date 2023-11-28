#!/bin/bash

# Define variables
SCRIPT_NAME="./main.py"   # Replace with your Python script name

# Start the Python script in the background
start() {
    if [ -f "$SCRIPT_NAME" ]; then
        nohup python3 "$SCRIPT_NAME" > output.log 2>&1 &
        echo "Started $SCRIPT_NAME in the background."
    else
        echo "$SCRIPT_NAME not found. Make sure the script is in the same directory."
    fi
}

# Pull the latest code from the GitHub repository
pull() {
    git pull
    echo "Pulled the latest code."
}

# Stop the running Python script
stop() {
    pkill -f "$SCRIPT_NAME"
    echo "Stopped $SCRIPT_NAME."
}

# Main script
case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        stop
        start
        ;;
    pull)
        pull
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|pull}"
        exit 1
        ;;
esac

exit 0
