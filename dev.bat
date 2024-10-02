@echo off

start "Bun Client" cmd /c "cd ./client && bun run dev"
start "FastAPI Server" cmd /c "cd ./server && python ./runner.py"
