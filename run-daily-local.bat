@echo off
rem Chay job tren may nay, KHONG push. Vi du: run-daily-local.bat --date 2026-09-25
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
venv\Scripts\python -m job.run_daily --no-push --force %*
