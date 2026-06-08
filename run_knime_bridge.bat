@echo off
REM Healthcare Pipeline - KNIME Bridge Launcher
REM Double-click this file to start the bridge on port 9999.
REM The Flask API container will call it via http://host.docker.internal:9999

echo Starting KNIME Bridge...
echo   KNIME: %KNIME_EXECUTABLE%
echo   Workflow: %KNIME_WORKFLOW_PATH%
echo.
python "%~dp0knime_bridge.py"
pause
