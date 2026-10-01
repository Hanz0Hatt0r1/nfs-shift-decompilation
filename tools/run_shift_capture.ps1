[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [string]$GameExe,

    [Parameter(Mandatory=$true)]
    [string]$ProxyDll,

    [string]$OutputDir = ".\shift-capture",

    [ValidateSet("Passthrough", "Diagnostic", "Capture")]
    [string]$Mode = "Diagnostic",

    [string[]]$GameArgument = @(),

    [switch]$DebugOutput,

    [switch]$CaptureScreenshots,

    [switch]$CaptureTextureSnapshots,

    [string]$TextureStages = "0,3,4"
)

$ErrorActionPreference = "Stop"

$gamePath = (Resolve-Path $GameExe).Path
$proxyPath = (Resolve-Path $ProxyDll).Path
$gameDir = Split-Path -Parent $gamePath
$proxyName = Split-Path -Leaf $proxyPath

if ($proxyName -ine "d3d9.dll") {
    throw "Proxy DLL must be named d3d9.dll"
}

$targetDll = Join-Path $gameDir "d3d9.dll"
if ([IO.Path]::GetFullPath($proxyPath) -ieq [IO.Path]::GetFullPath($targetDll)) {
    throw "ProxyDll must not already be the game's d3d9.dll; use the built artifact as the source"
}

$out = [IO.Path]::GetFullPath($OutputDir)
New-Item -ItemType Directory -Force -Path $out | Out-Null

$capturePath = Join-Path $out "shift_d3d9_capture.jsonl"
$crashPath = Join-Path $out "shift_d3d9_crash.jsonl"
$sidecarDll = Join-Path $gameDir "d3d9.shift_backend.dll"
$backupDll = Join-Path $out "original_d3d9.dll"
$backupSidecar = Join-Path $out "original_d3d9.shift_backend.dll"
$hadDll = Test-Path $targetDll
$hadSidecar = Test-Path $sidecarDll
$stagedBackend = $false
$exitCode = 0

# Make all recovery copies before mutating the game directory.
if ($hadDll) {
    Copy-Item -LiteralPath $targetDll -Destination $backupDll -Force
}
if ($hadSidecar) {
    Copy-Item -LiteralPath $sidecarDll -Destination $backupSidecar -Force
}

$oldCapture = $env:SHIFT_D3D9_CAPTURE
$oldCrashLog = $env:SHIFT_D3D9_CRASH_LOG
$oldCrashDiagnostics = $env:SHIFT_D3D9_CRASH_DIAGNOSTICS
$oldMode = $env:SHIFT_D3D9_CAPTURE_MODE
$oldBackend = $env:SHIFT_D3D9_BACKEND
$oldDebugOutput = $env:SHIFT_D3D9_CAPTURE_DEBUG_OUTPUT
$oldScreenshots = $env:SHIFT_D3D9_CAPTURE_SCREENSHOT
$oldEvery = $env:SHIFT_D3D9_CAPTURE_SCREENSHOT_EVERY
$oldScreenshotDir = $env:SHIFT_D3D9_CAPTURE_SCREENSHOT_DIR
$oldTextureSnapshot = $env:SHIFT_D3D9_CAPTURE_TEXTURE_SNAPSHOT
$oldTextureSnapshotDir = $env:SHIFT_D3D9_CAPTURE_TEXTURE_SNAPSHOT_DIR
$oldTextureStages = $env:SHIFT_D3D9_CAPTURE_TEXTURE_STAGES

try {
    if ($hadSidecar) {
        Remove-Item -LiteralPath $sidecarDll -Force
    }

    if ($hadDll) {
        $existingHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $targetDll).Hash
        $proxyHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $proxyPath).Hash
        if ($existingHash -ne $proxyHash) {
            Copy-Item -LiteralPath $targetDll -Destination $sidecarDll -Force
            $stagedBackend = $true
        }
    }

    Copy-Item -LiteralPath $proxyPath -Destination $targetDll -Force

    $env:SHIFT_D3D9_CAPTURE = $capturePath
    $env:SHIFT_D3D9_CRASH_LOG = $crashPath
    $env:SHIFT_D3D9_CRASH_DIAGNOSTICS = "1"
    $env:SHIFT_D3D9_CAPTURE_MODE = $Mode.ToLowerInvariant()
    if ($stagedBackend) {
        $env:SHIFT_D3D9_BACKEND = $sidecarDll
    } else {
        Remove-Item Env:SHIFT_D3D9_BACKEND -ErrorAction SilentlyContinue
    }
    if ($DebugOutput) {
        $env:SHIFT_D3D9_CAPTURE_DEBUG_OUTPUT = "1"
    } else {
        Remove-Item Env:SHIFT_D3D9_CAPTURE_DEBUG_OUTPUT -ErrorAction SilentlyContinue
    }

    if ($CaptureScreenshots) {
        $env:SHIFT_D3D9_CAPTURE_SCREENSHOT = "1"
        $env:SHIFT_D3D9_CAPTURE_SCREENSHOT_EVERY = "1"
        $env:SHIFT_D3D9_CAPTURE_SCREENSHOT_DIR = (Join-Path $out "frames")
        New-Item -ItemType Directory -Force -Path $env:SHIFT_D3D9_CAPTURE_SCREENSHOT_DIR | Out-Null
    }
    if ($CaptureTextureSnapshots) {
        $env:SHIFT_D3D9_CAPTURE_TEXTURE_SNAPSHOT = "1"
        $env:SHIFT_D3D9_CAPTURE_TEXTURE_STAGES = $TextureStages
        $env:SHIFT_D3D9_CAPTURE_TEXTURE_SNAPSHOT_DIR = (Join-Path $out "textures")
        New-Item -ItemType Directory -Force -Path $env:SHIFT_D3D9_CAPTURE_TEXTURE_SNAPSHOT_DIR | Out-Null
    }

    Write-Host "Launching: $gamePath"
    Write-Host "Capture : $capturePath"
    Write-Host "Crash   : $crashPath"
    Write-Host "Mode    : $Mode"
    if ($stagedBackend) {
        Write-Host "Backend : preserved local d3d9.dll via $sidecarDll"
    } else {
        Write-Host "Backend : system d3d9.dll"
    }
    if ($CaptureScreenshots) {
        Write-Host "Frames  : $env:SHIFT_D3D9_CAPTURE_SCREENSHOT_DIR"
    }
    if ($CaptureTextureSnapshots) {
        Write-Host "Textures: $env:SHIFT_D3D9_CAPTURE_TEXTURE_SNAPSHOT_DIR (stages $TextureStages)"
    }

    $process = Start-Process -FilePath $gamePath -ArgumentList $GameArgument -WorkingDirectory $gameDir -PassThru
    Wait-Process -Id $process.Id
    $exitCode = $process.ExitCode
}
finally {
    if ($hadDll) {
        Copy-Item -LiteralPath $backupDll -Destination $targetDll -Force
    } else {
        Remove-Item -LiteralPath $targetDll -Force -ErrorAction SilentlyContinue
    }

    if ($hadSidecar) {
        Copy-Item -LiteralPath $backupSidecar -Destination $sidecarDll -Force
    } else {
        Remove-Item -LiteralPath $sidecarDll -Force -ErrorAction SilentlyContinue
    }

    if ($null -eq $oldCapture) { Remove-Item Env:SHIFT_D3D9_CAPTURE -ErrorAction SilentlyContinue } else { $env:SHIFT_D3D9_CAPTURE = $oldCapture }
    if ($null -eq $oldCrashLog) { Remove-Item Env:SHIFT_D3D9_CRASH_LOG -ErrorAction SilentlyContinue } else { $env:SHIFT_D3D9_CRASH_LOG = $oldCrashLog }
    if ($null -eq $oldCrashDiagnostics) { Remove-Item Env:SHIFT_D3D9_CRASH_DIAGNOSTICS -ErrorAction SilentlyContinue } else { $env:SHIFT_D3D9_CRASH_DIAGNOSTICS = $oldCrashDiagnostics }
    if ($null -eq $oldMode) { Remove-Item Env:SHIFT_D3D9_CAPTURE_MODE -ErrorAction SilentlyContinue } else { $env:SHIFT_D3D9_CAPTURE_MODE = $oldMode }
    if ($null -eq $oldBackend) { Remove-Item Env:SHIFT_D3D9_BACKEND -ErrorAction SilentlyContinue } else { $env:SHIFT_D3D9_BACKEND = $oldBackend }
    if ($null -eq $oldDebugOutput) { Remove-Item Env:SHIFT_D3D9_CAPTURE_DEBUG_OUTPUT -ErrorAction SilentlyContinue } else { $env:SHIFT_D3D9_CAPTURE_DEBUG_OUTPUT = $oldDebugOutput }
    if ($null -eq $oldScreenshots) { Remove-Item Env:SHIFT_D3D9_CAPTURE_SCREENSHOT -ErrorAction SilentlyContinue } else { $env:SHIFT_D3D9_CAPTURE_SCREENSHOT = $oldScreenshots }
    if ($null -eq $oldEvery) { Remove-Item Env:SHIFT_D3D9_CAPTURE_SCREENSHOT_EVERY -ErrorAction SilentlyContinue } else { $env:SHIFT_D3D9_CAPTURE_SCREENSHOT_EVERY = $oldEvery }
    if ($null -eq $oldScreenshotDir) { Remove-Item Env:SHIFT_D3D9_CAPTURE_SCREENSHOT_DIR -ErrorAction SilentlyContinue } else { $env:SHIFT_D3D9_CAPTURE_SCREENSHOT_DIR = $oldScreenshotDir }
    if ($null -eq $oldTextureSnapshot) { Remove-Item Env:SHIFT_D3D9_CAPTURE_TEXTURE_SNAPSHOT -ErrorAction SilentlyContinue } else { $env:SHIFT_D3D9_CAPTURE_TEXTURE_SNAPSHOT = $oldTextureSnapshot }
    if ($null -eq $oldTextureSnapshotDir) { Remove-Item Env:SHIFT_D3D9_CAPTURE_TEXTURE_SNAPSHOT_DIR -ErrorAction SilentlyContinue } else { $env:SHIFT_D3D9_CAPTURE_TEXTURE_SNAPSHOT_DIR = $oldTextureSnapshotDir }
    if ($null -eq $oldTextureStages) { Remove-Item Env:SHIFT_D3D9_CAPTURE_TEXTURE_STAGES -ErrorAction SilentlyContinue } else { $env:SHIFT_D3D9_CAPTURE_TEXTURE_STAGES = $oldTextureStages }
}

if ($exitCode -ne 0) {
    Write-Warning "Game exited with code $exitCode; capture prefix may still be useful."
}

if (-not (Test-Path $capturePath)) {
    throw "No runtime capture was produced: $capturePath"
}

Get-Item $capturePath | Select-Object FullName, Length, LastWriteTime
if (Test-Path $crashPath) {
    $crash = Get-Item $crashPath
    if ($crash.Length -gt 0) {
        Write-Host "Crash context: $crashPath"
    }
}
Write-Host "Capture completed."
