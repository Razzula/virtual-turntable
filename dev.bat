@echo off

start "Bun Client" cmd /c "cd ./client && bun run dev"
start "FastAPI Server" cmd /c "cd ./server && call ./.venv/virtual-turntable/Scripts/activate && python ./runner.py"
