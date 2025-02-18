#!/bin/bash
# Determine the absolute directory where this script resides.
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SERVICE_NAME="teleg_bot.service"
SERVICE_PATH="/etc/systemd/system/$SERVICE_NAME"
FLAGFILE_INSTALL="$SCRIPT_DIR/venv/.completed_installation"
TMUX_SESSION="teleg_bot"

usage() {
    echo "Usage: $0 [--keepalive | --uninstall | --internal]"
    exit 1
}

# Only one argument allowed.
if [ "$#" -gt 1 ]; then
    usage
fi

# --keepalive: install (or update) a systemd service that runs the bot on reboot.
if [ "$1" == "--keepalive" ]; then
    echo "Installing/updating systemd service..."
    
    # Create virtual environment and install dependencies if needed.
    if [ ! -d "$SCRIPT_DIR/venv" ]; then
        python3 -m venv "$SCRIPT_DIR/venv"
    fi
    if [ ! -f "$FLAGFILE_INSTALL" ]; then
        "$SCRIPT_DIR/venv/bin/python3" -m pip install --upgrade pip
        "$SCRIPT_DIR/venv/bin/python3" -m pip install -U -r "$SCRIPT_DIR/requirements.txt"
        touch "$FLAGFILE_INSTALL"
    fi

    # Create a systemd service file.
    sudo tee "$SERVICE_PATH" > /dev/null <<EOF
[Unit]
Description=Telegram Bot Service
After=network.target

[Service]
Type=simple
WorkingDirectory=$SCRIPT_DIR
ExecStart=$SCRIPT_DIR/$(basename "$0") --internal
Restart=always
User=$(whoami)
Environment="PATH=$SCRIPT_DIR/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

[Install]
WantedBy=multi-user.target
EOF

    # Reload systemd and enable the service.
    sudo systemctl daemon-reload
    sudo systemctl enable "$SERVICE_NAME"
    sudo systemctl start "$SERVICE_NAME"
    echo "Service installed and started."
    exit 0

# --uninstall: remove the systemd service.
elif [ "$1" == "--uninstall" ]; then
    echo "Removing systemd service..."
    sudo systemctl stop "$SERVICE_NAME"
    sudo systemctl disable "$SERVICE_NAME"
    sudo rm -f "$SERVICE_PATH"
    sudo systemctl daemon-reload
    echo "Service removed."
    exit 0

# --internal: internal flag used by the systemd service to run the bot directly.
elif [ "$1" == "--internal" ]; then
    # Setup the environment (in case it was not set up yet).
    if [ ! -d "$SCRIPT_DIR/venv" ]; then
        python3 -m venv "$SCRIPT_DIR/venv"
    fi
    if [ ! -f "$FLAGFILE_INSTALL" ]; then
        "$SCRIPT_DIR/venv/bin/python3" -m pip install --upgrade pip
        "$SCRIPT_DIR/venv/bin/python3" -m pip install -U -r "$SCRIPT_DIR/requirements.txt"
        touch "$FLAGFILE_INSTALL"
    fi
    # Run the bot process directly (no tmux).
    exec "$SCRIPT_DIR/venv/bin/python3" bot.py
    exit 0
elif [ -n "$1" ]; then
    usage
fi

# Default behavior (no flag): install venv/dependencies and launch bot in a tmux session.
if [ ! -d "$SCRIPT_DIR/venv" ]; then
    python3 -m venv "$SCRIPT_DIR/venv"
fi
if [ ! -f "$FLAGFILE_INSTALL" ]; then
    "$SCRIPT_DIR/venv/bin/python3" -m pip install --upgrade pip
    "$SCRIPT_DIR/venv/bin/python3" -m pip install -U -r "$SCRIPT_DIR/requirements.txt"
    touch "$FLAGFILE_INSTALL"
fi
if ! command -v tmux &> /dev/null; then
    sudo apt-get install tmux
fi
if [ -z "$(tmux list-sessions | grep $TMUX_SESSION)" ]; then
    echo "Starting tmux session $TMUX_SESSION (kill with: tmux kill-session -t $TMUX_SESSION)"
    tmux new-session -d -s $TMUX_SESSION 'venv/bin/python3 bot.py && exit'
fi
