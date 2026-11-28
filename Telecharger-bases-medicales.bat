@echo off
setlocal
where py >nul 2>nul
if errorlevel 1 (
    python "%~dp0scripts\download_medical_sources.py" %*
) else (
    py -3 "%~dp0scripts\download_medical_sources.py" %*
)
exit /b %errorlevel%
