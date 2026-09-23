# Install ma3-mcp + Storan helpers on WS1 (Windows onPC)
$ErrorActionPreference = 'Stop'

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptDir '..\..')

Write-Host "Repo: $RepoRoot"

# Python 3.11+
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { Write-Error 'python not found; install Python 3.11+' }
$ver = & python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
Write-Host "Python $ver"
if ([version]$ver -lt [version]'3.11') { Write-Error 'Python 3.11+ required' }

# IPC directory
$IpcDir = if ($env:MA3_IPC_DIR) { $env:MA3_IPC_DIR } else { 'C:\ProgramData\MA3' }
New-Item -ItemType Directory -Force -Path $IpcDir | Out-Null
Write-Host "IPC dir: $IpcDir"

Set-Location $RepoRoot

# Dependencies
$poetry = Get-Command poetry -ErrorAction SilentlyContinue
if ($poetry) {
    Write-Host 'Installing with Poetry...'
    poetry install
} else {
    Write-Host 'Poetry not found; pip install -e .'
    python -m pip install -e .
}

# Deploy plugin
& (Join-Path $ScriptDir 'deploy-windows.ps1')

Write-Host ''
Write-Host '=== IPC self-test (requires onPC + MCP plugin running) ==='
Write-Host '  poetry run python storan/ma3_robust.py'
Write-Host '  or: .\storan\scripts\self-test-ipc.ps1'
Write-Host ''
Write-Host 'Start onPC with plugin:'
Write-Host '  .\storan\scripts\start-onpc-with-mcp.ps1'
