# Start NetBird HTTP bridge + grandMA3 onPC with MCP plugin (RUNPLUGIN cold start)
$ErrorActionPreference = 'Stop'

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptDir '..\..')

function Start-NetbirdHttpBridge {
    $bridge = Join-Path $RepoRoot 'run_netbird_http.py'
    if (-not (Test-Path $bridge)) {
        Write-Host 'run_netbird_http.py not in repo; skipping NetBird HTTP bridge'
        return
    }

    $port = if ($env:MA3_HTTP_PORT) { $env:MA3_HTTP_PORT } else { '8765' }
    $existing = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    if ($existing) {
        Write-Host "NetBird HTTP bridge already listening on port $port"
        return
    }

    Write-Host "Starting NetBird HTTP bridge on port $port..."
    $poetry = Get-Command poetry -ErrorAction SilentlyContinue
    if ($poetry) {
        Start-Process -FilePath 'poetry' -ArgumentList @(
            'run', 'python', 'run_netbird_http.py'
        ) -WorkingDirectory $RepoRoot -WindowStyle Hidden
    } else {
        Start-Process -FilePath 'python' -ArgumentList @(
            'run_netbird_http.py'
        ) -WorkingDirectory $RepoRoot -WindowStyle Hidden
    }
}

function Write-AutoloadGo {
    param([string]$IpcDir)
    New-Item -ItemType Directory -Force -Path $IpcDir | Out-Null
    $autoload = Join-Path $IpcDir 'mcp_autoload.txt'
    Set-Content -Path $autoload -Value 'go' -NoNewline -Encoding ascii
    Write-Host "Wrote $autoload = go"
}

function Wait-ForMcpAutoload {
    param(
        [string]$IpcDir,
        [int]$TimeoutSec = 180
    )
    $autoload = Join-Path $IpcDir 'mcp_autoload.txt'
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    Write-Host "Watching mcp_autoload.txt for done (timeout ${TimeoutSec}s)..."

    while ((Get-Date) -lt $deadline) {
        if (Test-Path $autoload) {
            $content = Get-Content -Path $autoload -Raw -ErrorAction SilentlyContinue
            if ($content -and ($content.Trim() -eq 'done')) {
                Write-Host 'MCP autoload complete (mcp_autoload.txt=done)'
                return $true
            }
        }
        Start-Sleep -Seconds 2
    }

    Write-Warning 'Timed out waiting for mcp_autoload.txt=done (plugin may still be loading)'
    return $false
}

Start-NetbirdHttpBridge

$IpcDir = if ($env:MA3_IPC_DIR) { $env:MA3_IPC_DIR } else { 'C:\ProgramData\MA3' }
Write-AutoloadGo -IpcDir $IpcDir

$DefaultBin = 'C:\Program Files\MALightingTechnology\gma3_2.3.2\bin\app_gma3.exe'
$Bin = if ($env:GMA3_BIN) { $env:GMA3_BIN } else { $DefaultBin }
if (-not (Test-Path $Bin)) {
    Write-Error "app_gma3.exe not found at $Bin - set GMA3_BIN to your onPC binary"
}

# RUNPLUGIN: lib_plugins XML name; -1 = first Lua component (mcp_server.lua)
$RunPluginArg = 'RUNPLUGIN="MCP Server.xml"-1'
Write-Host "Starting onPC: $Bin $RunPluginArg"
Start-Process -FilePath $Bin -ArgumentList @($RunPluginArg)

$timeout = if ($env:MCP_START_TIMEOUT) { [int]$env:MCP_START_TIMEOUT } else { 180 }
Wait-ForMcpAutoload -IpcDir $IpcDir -TimeoutSec $timeout | Out-Null

Set-Location $RepoRoot
Write-Host ''
Write-Host 'Verify IPC: .\storan\scripts\self-test-ipc.ps1'
Write-Host '  or: poetry run python -c "from ma3_mcp.ma3_comm import cmd; print(cmd(''Version''))"'
