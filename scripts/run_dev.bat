@echo off
cd /d "%~dp0\.."
python -m pip install -e .
python -m drivemind
pause
