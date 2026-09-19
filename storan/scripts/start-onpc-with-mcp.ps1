# Start grandMA3 onPC and auto-run MCP Server plugin (component 1)
$ErrorActionPreference = 'Stop'

$DefaultBin = 'C:\Program Files\MALightingTechnology\gma3_2.3.2\bin\app_gma3.exe'
$Bin = if ($env:GMA3_BIN) { $env:GMA3_BIN } else { $DefaultBin }

if (-not (Test-Path $Bin)) {
    Write-Error "app_gma3.exe not found at $Bin — set GMA3_BIN to your onPC binary"
}

# RUNPLUGIN uses plugin XML name from lib_plugins; -1 = first Lua component
$Args = 'RUNPLUGIN="MCP Server.xml"-1'
Write-Host "Starting: $Bin $Args"
Start-Process -FilePath $Bin -ArgumentList $Args

Write-Host 'Wait for onPC to load, then run: .\storan\scripts\self-test-ipc.ps1'
