# Version / IPC self-test against running onPC MCP plugin
$ErrorActionPreference = 'Stop'

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptDir '..\..')
Set-Location $RepoRoot

$IpcDir = if ($env:MA3_IPC_DIR) { $env:MA3_IPC_DIR } else { 'C:\ProgramData\MA3' }
if (-not (Test-Path $IpcDir)) {
    Write-Warning "IPC dir missing: $IpcDir (create before first run)"
}

Write-Host 'Running ma3_robust probe self-test...'
$poetry = Get-Command poetry -ErrorAction SilentlyContinue
if ($poetry) {
    poetry run python storan/ma3_robust.py
} else {
    python storan/ma3_robust.py
}

if ($LASTEXITCODE -ne 0) {
    Write-Error 'IPC self-test failed. Ensure onPC is running and MCP Server plugin is started.'
}
Write-Host 'IPC self-test finished.'
