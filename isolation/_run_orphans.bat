@echo off
cd /d "%~dp0"
"..\\.venv\Scripts\python.exe" cleanup_orphans.py 2
pause
