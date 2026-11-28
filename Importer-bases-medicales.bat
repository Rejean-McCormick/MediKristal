@echo off
setlocal
set "MEDIKRISTAL_IMPORT_DEFAULT="
if "%~1"=="" set "MEDIKRISTAL_IMPORT_DEFAULT=build"
where py >nul 2>nul
if errorlevel 1 (
    python "%~dp0scripts\import_medical_sources.py" %MEDIKRISTAL_IMPORT_DEFAULT% %*
) else (
    py -3 "%~dp0scripts\import_medical_sources.py" %MEDIKRISTAL_IMPORT_DEFAULT% %*
)
exit /b %errorlevel%
