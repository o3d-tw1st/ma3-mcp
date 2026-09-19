# Deploy MCP Server plugin to grandMA3 onPC (Windows)
$ErrorActionPreference = 'Stop'

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptDir '..\..')
$PluginSrc = Join-Path $RepoRoot 'plugin'

function Get-Ma3PluginDir {
    if ($env:MA3_PLUGIN_DIR) {
        return $env:MA3_PLUGIN_DIR
    }
    $candidates = @(
        (Join-Path $env:USERPROFILE 'MALightingTechnology'),
        'C:\ProgramData\MALightingTechnology',
        (Join-Path $env:USERPROFILE 'Documents\MALightingTechnology')
    )
    foreach ($base in $candidates) {
        if (-not (Test-Path $base)) { continue }
        $versions = Get-ChildItem -Path $base -Directory -Filter 'gma3_*' |
            Sort-Object Name -Descending
        foreach ($v in $versions) {
            $dir = Join-Path $v.FullName 'shared\resource\lib_plugins\mcp_server'
            if (Test-Path (Split-Path $dir -Parent)) { return $dir }
        }
    }
    return $null
}

$Ma3PluginDir = Get-Ma3PluginDir
if (-not $Ma3PluginDir) {
    Write-Error 'MA3_PLUGIN_DIR not set and auto-detect failed. Set env MA3_PLUGIN_DIR to ...\lib_plugins\mcp_server'
}

$Ma3LibraryDir = $Ma3PluginDir -replace 'shared\\resource\\lib_plugins', 'gma3_library\datapools\plugins'
New-Item -ItemType Directory -Force -Path $Ma3PluginDir | Out-Null
New-Item -ItemType Directory -Force -Path $Ma3LibraryDir | Out-Null

Write-Host "Copying plugin to $Ma3PluginDir"
Copy-Item (Join-Path $PluginSrc 'mcp_server.lua') $Ma3PluginDir -Force
Copy-Item (Join-Path $PluginSrc 'MCP Server.xml') $Ma3PluginDir -Force
Copy-Item (Join-Path $PluginSrc 'mcp_server.lua') $Ma3LibraryDir -Force
Copy-Item (Join-Path $PluginSrc 'MCP Server.xml') $Ma3LibraryDir -Force

$OscHost = if ($env:MA3_OSC_HOST) { $env:MA3_OSC_HOST } else { '127.0.0.1' }
$OscPort = if ($env:MA3_OSC_PORT) { [int]$env:MA3_OSC_PORT } else { 8000 }

Write-Host "OSC reload $OscHost`:$OscPort (optional; requires onPC listening)"
python -c @"
import socket, time

def send_osc(ip, port, address, message):
    ap = address + '\0' * (4 - len(address) % 4)
    tt = ',s' + '\0\0'
    mp = message + '\0' * (4 - len(message) % 4)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto((ap + tt + mp).encode(), (ip, port))
    sock.close()

send_osc('$OscHost', $OscPort, '/cmd', 'Off Plugin 1')
time.sleep(0.5)
send_osc('$OscHost', $OscPort, '/cmd', 'ReloadAllPlugins')
time.sleep(0.5)
send_osc('$OscHost', $OscPort, '/cmd', 'Call Plugin 1')
"@

Write-Host 'Deploy complete.'
