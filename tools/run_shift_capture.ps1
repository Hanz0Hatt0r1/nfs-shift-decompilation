[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [string]$GameExe,

    [Parameter(Mandatory=$true)]
    [string]$ProxyDll,

    [string]$OutputDir = ".\shift-capture",

    [string[]]$GameArgument = @(),

    [switch]$CaptureScreenshots
)

$ErrorActionPreference = "Stop"

$gamePath = (Resolve-Path $GameExe).Path
$proxyPath = (Resolve-Path $ProxyDll).Path
$gameDir = Split-Path -Parent $gamePath
$proxyName = Split-Path -Leaf $proxyPath

if ($proxyName -ine "d3d9.dll") {
    throw "Proxy DLL must be named d3d9.dll"
}

$out = [IO.Path]::GetFullPath($OutputDir)
New-Item -ItemType Directory -Force -Path $out | Out-Null

$capturePath = Join-Path $out "shift_d3d9_capture.jsonl"
$previousDll = Join-Path $gameDir "d3d9.dll"
$backupDll = $null

if (Test-Path $previousDll) {
    $backupDll = Join-Path $out "original_d3d9.dll"
    Copy-Item -LiteralPath $previousDll -Destination $backupDll -Force
}

Copy-Item -LiteralPath $proxyPath -Destination $previousDll -Force

$oldCapture = $env:SHIFT_D3D9_CAPTURE
$oldScreenshots = $env:SHIFT_D3D9_CAPTURE_SCREENSHOT
$oldEvery = $env:SHIFT_D3D9_CAPTURE_SCREENSHOT_EVERY
$oldScreenshotDir = $env:SHIFT_D3D9_CAPTURE_SCREENSHOT_DIR

try {
    $env:SHIFT_D3D9_CAPTURE = $capturePath
    if ($CaptureScreenshots) {
        $env:SHIFT_D3D9_CAPTURE_SCREENSHOT = "1"
        $env:SHIFT_D3D9_CAPTURE_SCREENSHOT_EVERY = "1"
        $env:SHIFT_D3D9_CAPTURE_SCREENSHOT_DIR = (Join-Path $out "frames")
        New-Item -ItemType Directory -Force -Path $env:SHIFT_D3D9_CAPTURE_SCREENSHOT_DIR | Out-Null
    }

    Write-Host "Launching: $gamePath"
    Write-Host "Capture : $capturePath"
    if ($CaptureScreenshots) {
        Write-Host "Frames  : $env:SHIFT_D3D9_CAPTURE_SCREENSHOT_DIR"
    }

    $process = Start-Process -FilePath $gamePath -ArgumentList $GameArgument -WorkingDirectory $gameDir -PassThru
    Wait-Process -Id $process.Id
    $exitCode = $process.ExitCode
}
finally {
    if ($backupDll) {
        Copy-Item -LiteralPath $backupDll -Destination $previousDll -Force
    } else {
        Remove-Item -LiteralPath $previousDll -Force -ErrorAction SilentlyContinue
    }

    if ($null -eq $oldCapture) { Remove-Item Env:SHIFT_D3D9_CAPTURE -ErrorAction SilentlyContinue } else { $env:SHIFT_D3D9_CAPTURE = $oldCapture }
    if ($null -eq $oldScreenshots) { Remove-Item Env:SHIFT_D3D9_CAPTURE_SCREENSHOT -ErrorAction SilentlyContinue } else { $env:SHIFT_D3D9_CAPTURE_SCREENSHOT = $oldScreenshots }
    if ($null -eq $oldEvery) { Remove-Item Env:SHIFT_D3D9_CAPTURE_SCREENSHOT_EVERY -ErrorAction SilentlyContinue } else { $env:SHIFT_D3D9_CAPTURE_SCREENSHOT_EVERY = $oldEvery }
    if ($null -eq $oldScreenshotDir) { Remove-Item Env:SHIFT_D3D9_CAPTURE_SCREENSHOT_DIR -ErrorAction SilentlyContinue } else { $env:SHIFT_D3D9_CAPTURE_SCREENSHOT_DIR = $oldScreenshotDir }
}

if ($exitCode -ne 0) {
    Write-Warning "Game exited with code $exitCode; capture prefix may still be useful."
}

if (-not (Test-Path $capturePath)) {
    throw "No runtime capture was produced: $capturePath"
}

Get-Item $capturePath | Select-Object FullName, Length, LastWriteTime
Write-Host "Capture completed."
