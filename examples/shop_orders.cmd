@echo off
setlocal
if "%~1"=="" (
  echo Launcher ready. No task started. Use launch with product, pages and session; use status for an existing session.
  exit /b 0
)
"%~dp0..\.venv\Scripts\python.exe" -X utf8 "%~dp0shop_orders.py" %*
exit /b %errorlevel%
