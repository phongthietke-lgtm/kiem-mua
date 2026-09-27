@echo off
rem Tao venv va cai thu vien. Chay mot lan tu thu muc kiem-mua.
cd /d "%~dp0"
if not exist venv (
  py -3.12 -m venv venv || python -m venv venv
)
venv\Scripts\python -m pip install -r requirements.txt
echo Xong. Chay test: venv\Scripts\python -m pytest -q
