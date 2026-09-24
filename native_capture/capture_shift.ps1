param(
  [Parameter(Mandatory = $true, Position = 0)]
  [string]$ShiftExe
)

$root = Join-Path $PSScriptRoot "capture-out"
$frames = Join-Path $root "frames"
$textures = Join-Path $root "textures"

New-Item -ItemType Directory -Force -Path $frames, $textures | Out-Null

$env:SHIFT_D3D9_CAPTURE = Join-Path $root "shift_m3_capture.jsonl"
$env:SHIFT_D3D9_CAPTURE_SCREENSHOT = "1"
$env:SHIFT_D3D9_CAPTURE_SCREENSHOT_EVERY = "1"
$env:SHIFT_D3D9_CAPTURE_SCREENSHOT_DIR = $frames
$env:SHIFT_D3D9_CAPTURE_TEXTURE_CONTENTS = "1"
$env:SHIFT_D3D9_CAPTURE_TEXTURE_DIR = $textures
$env:SHIFT_D3D9_CAPTURE_TEXTURE_STAGES = "0,3,4"

Write-Host "Capture: $env:SHIFT_D3D9_CAPTURE"
Write-Host "Screenshots: $env:SHIFT_D3D9_CAPTURE_SCREENSHOT_DIR"
Write-Host "Texture stages: $env:SHIFT_D3D9_CAPTURE_TEXTURE_STAGES"
Write-Host ""
Write-Host "Place the built d3d9.dll proxy beside Shift.exe before launching."

$workingDirectory = Split-Path -Parent (Resolve-Path $ShiftExe)
& $ShiftExe
exit $LASTEXITCODE
