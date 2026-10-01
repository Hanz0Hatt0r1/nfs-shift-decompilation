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

    [string]$TextureStages = "0,3,4",

    [long]$FrameStart = -1,

    [long]$FrameEnd = -1,

    [switch]$CaptureBufferPayloads,

    [switch]$CaptureTexturePayloads,

    [switch]$TriggerCapture,

    [string]$ResourceTrigger = "",

    [switch]$ResourceTriggerRepeat,

    [ValidateRange(0, 120)]
    [int]$PreFrames = 2,

    [ValidateRange(0, 120)]
    [int]$PostFrames = 2
)

$ErrorActionPreference = "Stop"

if ($FrameStart -lt -1 -or $FrameEnd -lt -1) {
    throw "FrameStart/FrameEnd must be -1 (unset) or non-negative"
}
if ($FrameStart -ge 0 -and $FrameEnd -ge 0 -and $FrameEnd -lt $FrameStart) {
    throw "FrameEnd must be >= FrameStart"
}
if (($TriggerCapture -or $ResourceTrigger) -and ($FrameStart -ge 0 -or $FrameEnd -ge 0)) {
    throw "TriggerCapture/ResourceTrigger cannot be combined with FrameStart/FrameEnd"
}

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
$oldFrameStart = $env:SHIFT_D3D9_CAPTURE_FRAME_START
$oldFrameEnd = $env:SHIFT_D3D9_CAPTURE_FRAME_END
$oldBufferPayloads = $env:SHIFT_D3D9_CAPTURE_BUFFER_PAYLOADS
$oldBufferPayloadDir = $env:SHIFT_D3D9_CAPTURE_BUFFER_PAYLOAD_DIR
$oldTexturePayloads = $env:SHIFT_D3D9_CAPTURE_TEXTURE_PAYLOADS
$oldTexturePayloadDir = $env:SHIFT_D3D9_CAPTURE_TEXTURE_PAYLOAD_DIR
$oldTrigger = $env:SHIFT_D3D9_CAPTURE_TRIGGER
$oldTriggerPre = $env:SHIFT_D3D9_CAPTURE_TRIGGER_PRE_FRAMES
$oldTriggerPost = $env:SHIFT_D3D9_CAPTURE_TRIGGER_POST_FRAMES
$oldTriggerKey = $env:SHIFT_D3D9_CAPTURE_TRIGGER_KEY
$oldTriggerFile = $env:SHIFT_D3D9_CAPTURE_TRIGGER_FILE
$oldResourceTrigger = $env:SHIFT_D3D9_CAPTURE_RESOURCE_TRIGGER
$oldResourceTriggerRepeat = $env:SHIFT_D3D9_CAPTURE_RESOURCE_TRIGGER_REPEAT

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
    if ($FrameStart -ge 0) { $env:SHIFT_D3D9_CAPTURE_FRAME_START = [string]$FrameStart } else { Remove-Item Env:SHIFT_D3D9_CAPTURE_FRAME_START -ErrorAction SilentlyContinue }
    if ($FrameEnd -ge 0) { $env:SHIFT_D3D9_CAPTURE_FRAME_END = [string]$FrameEnd } else { Remove-Item Env:SHIFT_D3D9_CAPTURE_FRAME_END -ErrorAction SilentlyContinue }
    $triggerFile = Join-Path $out "capture.trigger"
    if ($TriggerCapture -or $ResourceTrigger) {
        Remove-Item -LiteralPath $triggerFile -Force -ErrorAction SilentlyContinue
        $env:SHIFT_D3D9_CAPTURE_TRIGGER = "1"
        $env:SHIFT_D3D9_CAPTURE_TRIGGER_PRE_FRAMES = [string]$PreFrames
        $env:SHIFT_D3D9_CAPTURE_TRIGGER_POST_FRAMES = [string]$PostFrames
        $env:SHIFT_D3D9_CAPTURE_TRIGGER_KEY = "0x79"
        $env:SHIFT_D3D9_CAPTURE_TRIGGER_FILE = $triggerFile
        if ($ResourceTrigger) {
            $env:SHIFT_D3D9_CAPTURE_RESOURCE_TRIGGER = $ResourceTrigger
        } else {
            Remove-Item Env:SHIFT_D3D9_CAPTURE_RESOURCE_TRIGGER -ErrorAction SilentlyContinue
        }
        if ($ResourceTriggerRepeat) {
            $env:SHIFT_D3D9_CAPTURE_RESOURCE_TRIGGER_REPEAT = "1"
        } else {
            Remove-Item Env:SHIFT_D3D9_CAPTURE_RESOURCE_TRIGGER_REPEAT -ErrorAction SilentlyContinue
        }
    } else {
        Remove-Item Env:SHIFT_D3D9_CAPTURE_TRIGGER -ErrorAction SilentlyContinue
        Remove-Item Env:SHIFT_D3D9_CAPTURE_TRIGGER_PRE_FRAMES -ErrorAction SilentlyContinue
        Remove-Item Env:SHIFT_D3D9_CAPTURE_TRIGGER_POST_FRAMES -ErrorAction SilentlyContinue
        Remove-Item Env:SHIFT_D3D9_CAPTURE_TRIGGER_KEY -ErrorAction SilentlyContinue
        Remove-Item Env:SHIFT_D3D9_CAPTURE_TRIGGER_FILE -ErrorAction SilentlyContinue
        Remove-Item Env:SHIFT_D3D9_CAPTURE_RESOURCE_TRIGGER -ErrorAction SilentlyContinue
        Remove-Item Env:SHIFT_D3D9_CAPTURE_RESOURCE_TRIGGER_REPEAT -ErrorAction SilentlyContinue
    }
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
    if ($CaptureBufferPayloads) {
        $env:SHIFT_D3D9_CAPTURE_BUFFER_PAYLOADS = "1"
        $env:SHIFT_D3D9_CAPTURE_BUFFER_PAYLOAD_DIR = (Join-Path $out "buffers")
        New-Item -ItemType Directory -Force -Path $env:SHIFT_D3D9_CAPTURE_BUFFER_PAYLOAD_DIR | Out-Null
    } else {
        Remove-Item Env:SHIFT_D3D9_CAPTURE_BUFFER_PAYLOADS -ErrorAction SilentlyContinue
        Remove-Item Env:SHIFT_D3D9_CAPTURE_BUFFER_PAYLOAD_DIR -ErrorAction SilentlyContinue
    }
    if ($CaptureTexturePayloads) {
        $env:SHIFT_D3D9_CAPTURE_TEXTURE_PAYLOADS = "1"
        $env:SHIFT_D3D9_CAPTURE_TEXTURE_PAYLOAD_DIR = (Join-Path $out "texture-payloads")
        New-Item -ItemType Directory -Force -Path $env:SHIFT_D3D9_CAPTURE_TEXTURE_PAYLOAD_DIR | Out-Null
    } else {
        Remove-Item Env:SHIFT_D3D9_CAPTURE_TEXTURE_PAYLOADS -ErrorAction SilentlyContinue
        Remove-Item Env:SHIFT_D3D9_CAPTURE_TEXTURE_PAYLOAD_DIR -ErrorAction SilentlyContinue
    }

    Write-Host "Launching: $gamePath"
    Write-Host "Capture : $capturePath"
    Write-Host "Crash   : $crashPath"
    Write-Host "Mode    : $Mode"
    if ($FrameStart -ge 0 -or $FrameEnd -ge 0) {
        Write-Host "Frames  : $FrameStart..$FrameEnd"
    }
    if ($TriggerCapture -or $ResourceTrigger) {
        Write-Host "Trigger : F10 (pre=$PreFrames, post=$PostFrames)"
        Write-Host "          or create $triggerFile"
        if ($ResourceTrigger) { Write-Host "Resource: $ResourceTrigger" }
        if ($ResourceTriggerRepeat) { Write-Host "Repeat  : enabled" }
    }
    if ($CaptureBufferPayloads) { Write-Host "Buffers : $env:SHIFT_D3D9_CAPTURE_BUFFER_PAYLOAD_DIR" }
    if ($CaptureTexturePayloads) { Write-Host "Tex raw : $env:SHIFT_D3D9_CAPTURE_TEXTURE_PAYLOAD_DIR" }
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
    if ($null -eq $oldFrameStart) { Remove-Item Env:SHIFT_D3D9_CAPTURE_FRAME_START -ErrorAction SilentlyContinue } else { $env:SHIFT_D3D9_CAPTURE_FRAME_START = $oldFrameStart }
    if ($null -eq $oldFrameEnd) { Remove-Item Env:SHIFT_D3D9_CAPTURE_FRAME_END -ErrorAction SilentlyContinue } else { $env:SHIFT_D3D9_CAPTURE_FRAME_END = $oldFrameEnd }
    if ($null -eq $oldBufferPayloads) { Remove-Item Env:SHIFT_D3D9_CAPTURE_BUFFER_PAYLOADS -ErrorAction SilentlyContinue } else { $env:SHIFT_D3D9_CAPTURE_BUFFER_PAYLOADS = $oldBufferPayloads }
    if ($null -eq $oldBufferPayloadDir) { Remove-Item Env:SHIFT_D3D9_CAPTURE_BUFFER_PAYLOAD_DIR -ErrorAction SilentlyContinue } else { $env:SHIFT_D3D9_CAPTURE_BUFFER_PAYLOAD_DIR = $oldBufferPayloadDir }
    if ($null -eq $oldTexturePayloads) { Remove-Item Env:SHIFT_D3D9_CAPTURE_TEXTURE_PAYLOADS -ErrorAction SilentlyContinue } else { $env:SHIFT_D3D9_CAPTURE_TEXTURE_PAYLOADS = $oldTexturePayloads }
    if ($null -eq $oldTexturePayloadDir) { Remove-Item Env:SHIFT_D3D9_CAPTURE_TEXTURE_PAYLOAD_DIR -ErrorAction SilentlyContinue } else { $env:SHIFT_D3D9_CAPTURE_TEXTURE_PAYLOAD_DIR = $oldTexturePayloadDir }
    if ($null -eq $oldTrigger) { Remove-Item Env:SHIFT_D3D9_CAPTURE_TRIGGER -ErrorAction SilentlyContinue } else { $env:SHIFT_D3D9_CAPTURE_TRIGGER = $oldTrigger }
    if ($null -eq $oldTriggerPre) { Remove-Item Env:SHIFT_D3D9_CAPTURE_TRIGGER_PRE_FRAMES -ErrorAction SilentlyContinue } else { $env:SHIFT_D3D9_CAPTURE_TRIGGER_PRE_FRAMES = $oldTriggerPre }
    if ($null -eq $oldTriggerPost) { Remove-Item Env:SHIFT_D3D9_CAPTURE_TRIGGER_POST_FRAMES -ErrorAction SilentlyContinue } else { $env:SHIFT_D3D9_CAPTURE_TRIGGER_POST_FRAMES = $oldTriggerPost }
    if ($null -eq $oldTriggerKey) { Remove-Item Env:SHIFT_D3D9_CAPTURE_TRIGGER_KEY -ErrorAction SilentlyContinue } else { $env:SHIFT_D3D9_CAPTURE_TRIGGER_KEY = $oldTriggerKey }
    if ($null -eq $oldTriggerFile) { Remove-Item Env:SHIFT_D3D9_CAPTURE_TRIGGER_FILE -ErrorAction SilentlyContinue } else { $env:SHIFT_D3D9_CAPTURE_TRIGGER_FILE = $oldTriggerFile }
    if ($null -eq $oldResourceTrigger) { Remove-Item Env:SHIFT_D3D9_CAPTURE_RESOURCE_TRIGGER -ErrorAction SilentlyContinue } else { $env:SHIFT_D3D9_CAPTURE_RESOURCE_TRIGGER = $oldResourceTrigger }
    if ($null -eq $oldResourceTriggerRepeat) { Remove-Item Env:SHIFT_D3D9_CAPTURE_RESOURCE_TRIGGER_REPEAT -ErrorAction SilentlyContinue } else { $env:SHIFT_D3D9_CAPTURE_RESOURCE_TRIGGER_REPEAT = $oldResourceTriggerRepeat }
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
