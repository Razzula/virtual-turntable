#!/bin/bash

# Start Bun Client
gnome-terminal -- bash -c "cd ./client && bun run dev; exec bash"

# Start FastAPI Server
gnome-terminal -- bash -c "cd ./server && source ./.venv/virtual-turntable/bin/activate && python3 ./runner.py; exec bash"

