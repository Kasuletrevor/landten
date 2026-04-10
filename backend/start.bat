@echo off
REM Start LandTen backend (development mode)
REM Config is loaded from .env by python-dotenv in app/core/config.py
REM No manual env var setup needed.

cd /d "%~dp0"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
