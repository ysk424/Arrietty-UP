param(
    [string]$BlenderPath = "C:\Users\azoo\git\build_upbge_windows_Release_x64_vc17_Release\bin\blender.exe"
)

$ErrorActionPreference = "Stop"
$BlendPath = Join-Path $PSScriptRoot "Arrietty-UP.blend"
$Launcher = Join-Path $PSScriptRoot "tools\launch_live_test.ps1"

if (-not (Test-Path -LiteralPath $Launcher)) {
    throw "Arrietty launcher not found: $Launcher"
}

& $Launcher -BlenderPath $BlenderPath -BlendPath $BlendPath
