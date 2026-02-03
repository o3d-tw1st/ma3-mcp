#!/bin/bash
# Deploy MCP Server plugin to MA3 and reload
#
# For plugin reload to work, the plugin must be configured with:
#   - Installed = Yes
#   - IsResource = No (import from gma3_library/datapools/plugins/)
#
# See: https://forum.malighting.com/forum/thread/68211-grandma3-vscode-workflow/
#
# Configuration:
#   Set MA3_PLUGIN_DIR environment variable or create .env file with:
#   MA3_PLUGIN_DIR=/path/to/MALightingTechnology/gma3_X.X.X/shared/resource/lib_plugins/mcp_server
#
#   Set MA3_OSC_PORT for OSC reload (default: 8000)
#   Set MA3_OSC_HOST for remote console (default: 127.0.0.1)

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Load .env file if it exists
if [[ -f "$SCRIPT_DIR/.env" ]]; then
    export $(grep -v '^#' "$SCRIPT_DIR/.env" | xargs)
fi

# Auto-detect MA3 plugin directory if not set
if [[ -z "$MA3_PLUGIN_DIR" ]]; then
    # Try to find MALightingTechnology folder
    if [[ -d "$HOME/MALightingTechnology" ]]; then
        # Find gma3 version directories (e.g., gma3_2.3.2), excluding non-version dirs
        # Only match directories like gma3_X.X.X (with version numbers)
        MA3_VERSION=$(ls -1 "$HOME/MALightingTechnology" | grep -E "^gma3_[0-9]+\.[0-9]+" | sort -V | tail -1)
        if [[ -n "$MA3_VERSION" ]]; then
            MA3_PLUGIN_DIR="$HOME/MALightingTechnology/$MA3_VERSION/shared/resource/lib_plugins/mcp_server"
        fi
    fi
fi

if [[ -z "$MA3_PLUGIN_DIR" ]]; then
    echo "❌ Error: MA3_PLUGIN_DIR not set and could not auto-detect."
    echo ""
    echo "Please set MA3_PLUGIN_DIR in your environment or .env file:"
    echo "  export MA3_PLUGIN_DIR=/path/to/MALightingTechnology/gma3_X.X.X/shared/resource/lib_plugins/mcp_server"
    echo ""
    echo "Or create a .env file in the project root with:"
    echo "  MA3_PLUGIN_DIR=/path/to/MALightingTechnology/gma3_X.X.X/shared/resource/lib_plugins/mcp_server"
    exit 1
fi

# OSC configuration with defaults
MA3_OSC_HOST="${MA3_OSC_HOST:-127.0.0.1}"
MA3_OSC_PORT="${MA3_OSC_PORT:-8000}"

# Create plugin directory if it doesn't exist
mkdir -p "$MA3_PLUGIN_DIR"

# Also deploy to gma3_library datapools (where ReloadAllPlugins looks)
MA3_LIBRARY_DIR=$(echo "$MA3_PLUGIN_DIR" | sed 's|shared/resource/lib_plugins|gma3_library/datapools/plugins|')
mkdir -p "$MA3_LIBRARY_DIR"

echo "📦 Copying plugin files to MA3..."
echo "   Resource: $MA3_PLUGIN_DIR/"
echo "   Library:  $MA3_LIBRARY_DIR/"
cp "$SCRIPT_DIR/plugin/mcp_server.lua" "$MA3_PLUGIN_DIR/"
cp "$SCRIPT_DIR/plugin/MCP Server.xml" "$MA3_PLUGIN_DIR/"
cp "$SCRIPT_DIR/plugin/mcp_server.lua" "$MA3_LIBRARY_DIR/"
cp "$SCRIPT_DIR/plugin/MCP Server.xml" "$MA3_LIBRARY_DIR/"

echo "🔄 Sending OSC reload command to $MA3_OSC_HOST:$MA3_OSC_PORT..."
python3 -c "
import socket
import time

def send_osc(ip, port, address, message):
    # Build OSC message
    address_padded = address + '\0' * (4 - len(address) % 4)
    type_tag = ',s' + '\0\0'
    message_padded = message + '\0' * (4 - len(message) % 4)
    packet = address_padded.encode() + type_tag.encode() + message_padded.encode()
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(packet, (ip, port))
    sock.close()

# 1. Stop plugin first (frees the Lua state)
send_osc('$MA3_OSC_HOST', $MA3_OSC_PORT, '/cmd', 'Off Plugin 1')
time.sleep(0.5)

# 2. Reload plugins from disk (updates Lua code from external files)
send_osc('$MA3_OSC_HOST', $MA3_OSC_PORT, '/cmd', 'ReloadAllPlugins')
time.sleep(0.5)

# 3. Start plugin again (loads fresh Lua code)
send_osc('$MA3_OSC_HOST', $MA3_OSC_PORT, '/cmd', 'Call Plugin 1')
"

echo "✅ Done! Plugin reloaded."
