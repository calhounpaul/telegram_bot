FLAGFILE_INSTALL="venv/.completed_installation"
TMUX_SESSION=teleg_bot

if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

if [ ! -f $FLAGFILE_INSTALL ]; then
    venv/bin/python3 -m pip install --upgrade pip
    venv/bin/python3 -m pip install -U -r requirements.txt
    touch $FLAGFILE_INSTALL
fi

if ! command -v tmux &> /dev/null
then
    sudo apt-get install tmux
fi


if [ -z "$(tmux list-sessions | grep $TMUX_SESSION)" ]; then
    echo "Starting tmux session $TMUX_SESSION (kill with command \"tmux kill-session -t $TMUX_SESSION\")"
    tmux new-session -d -s $TMUX_SESSION \
        'venv/bin/python3 bot.py && exit'
fi
