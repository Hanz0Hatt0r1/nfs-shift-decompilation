@echo off
setlocal

if "%~1"=="" (
  echo Usage: capture_shift.bat ^<path-to-Shift.exe^>
  exit /b 2
)

set "CAPTURE_ROOT=%~dp0capture-out"
if not exist "%CAPTURE_ROOT%" mkdir "%CAPTURE_ROOT%"
if not exist "%CAPTURE_ROOT%\frames" mkdir "%CAPTURE_ROOT%\frames"
if not exist "%CAPTURE_ROOT%\textures" mkdir "%CAPTURE_ROOT%\textures"

set "SHIFT_D3D9_CAPTURE=%CAPTURE_ROOT%\shift_m3_capture.jsonl"
set "SHIFT_D3D9_CAPTURE_SCREENSHOT=1"
set "SHIFT_D3D9_CAPTURE_SCREENSHOT_EVERY=1"
set "SHIFT_D3D9_CAPTURE_SCREENSHOT_DIR=%CAPTURE_ROOT%\frames"
set "SHIFT_D3D9_CAPTURE_TEXTURE_CONTENTS=1"
set "SHIFT_D3D9_CAPTURE_TEXTURE_DIR=%CAPTURE_ROOT%\textures"
set "SHIFT_D3D9_CAPTURE_TEXTURE_STAGES=0,3,4"

echo Capture: %SHIFT_D3D9_CAPTURE%
echo Screenshots: %SHIFT_D3D9_CAPTURE_SCREENSHOT_DIR%
echo Texture stages: %SHIFT_D3D9_CAPTURE_TEXTURE_STAGES%
echo.
echo Place the built d3d9.dll proxy beside Shift.exe before launching.
echo Stop the game after the BMW M3 is visible and inspect the JSONL/PPM outputs.
echo.

pushd "%~dp1"
"%~1"
set "EXIT_CODE=%ERRORLEVEL%"
popd

exit /b %EXIT_CODE%
