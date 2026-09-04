param(
    [string]$BlenderPath = "C:\Users\azoo\git\build_upbge_windows_Release_x64_vc17_Release\bin\blender.exe",
    [string]$BlendPath = "C:\Users\azoo\git\Arrietty-UP\Arrietty-UP.blend",
    [switch]$WaitForGoogleTiles
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$StartupScript = Join-Path $PSScriptRoot "launch_openxr_game.py"

$ExistingGame = Get-Process -Name blender, blenderplayer -ErrorAction SilentlyContinue
if ($ExistingGame) {
    $ProcessNames = ($ExistingGame.ProcessName | Sort-Object -Unique) -join ", "
    throw "A Blender/UPBGE process is already running ($ProcessNames). Stop it before a live test."
}
if (-not (Get-Process -Name vrserver -ErrorAction SilentlyContinue)) {
    throw "SteamVR is not running. Start SteamVR and confirm the HMD first."
}
if (-not (Test-Path -LiteralPath $BlenderPath)) {
    throw "UPBGE executable not found: $BlenderPath"
}
if (-not (Test-Path -LiteralPath $BlendPath)) {
    throw "Project blend not found: $BlendPath"
}

$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$Stdout = Join-Path $env:TEMP "arrietty-live-$Stamp.out.log"
$Stderr = Join-Path $env:TEMP "arrietty-live-$Stamp.err.log"
$PreviousWaitForTiles = $env:ARRIETTY_WAIT_FOR_GOOGLE_TILES
$PreviousProjectRoot = $env:ARRIETTY_PROJECT_ROOT
try {
    $env:ARRIETTY_WAIT_FOR_GOOGLE_TILES = if ($WaitForGoogleTiles) { "1" } else { "0" }
    $env:ARRIETTY_PROJECT_ROOT = $ProjectRoot
    $Process = Start-Process `
        -FilePath $BlenderPath `
        -ArgumentList @("--online-mode", "--start-console", $BlendPath, "--python", $StartupScript) `
        -RedirectStandardOutput $Stdout `
        -RedirectStandardError $Stderr `
        -PassThru
}
finally {
    if ($null -eq $PreviousWaitForTiles) {
        Remove-Item Env:\ARRIETTY_WAIT_FOR_GOOGLE_TILES -ErrorAction SilentlyContinue
    }
    else {
        $env:ARRIETTY_WAIT_FOR_GOOGLE_TILES = $PreviousWaitForTiles
    }
    if ($null -eq $PreviousProjectRoot) {
        Remove-Item Env:\ARRIETTY_PROJECT_ROOT -ErrorAction SilentlyContinue
    }
    else {
        $env:ARRIETTY_PROJECT_ROOT = $PreviousProjectRoot
    }
}

[pscustomobject]@{
    ProcessId = $Process.Id
    Project = $ProjectRoot
    StandardOutput = $Stdout
    StandardError = $Stderr
    WaitForGoogleTiles = [bool]$WaitForGoogleTiles
} | Format-List
