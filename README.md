# MA3-MCP

> ⚠️ **Prototype / Proof of Concept**  
> This project is an experimental implementation demonstrating AI-assisted lighting control via MCP.
> It is not intended for production use. Use at your own risk.

MCP server for controlling grandMA3 lighting consoles via AI assistants (Claude Desktop, VS Code Copilot, etc.).

## Features

- Execute MA3 console commands directly
- Control fixtures (dimmer, color, position, gobo, etc.)
- Store and manage cues with timing and triggers
- Playback control (Go, Back, Off, etc.)
- Executor fader and button control
- Query sequences, cues, and programmer contents
- Read DMX output
- Group support with batch operations

## Project Structure

```
ma3_mcp/
├── config.py      # Configuration management
├── ma3_comm.py    # File-based IPC with grandMA3
├── server.py      # MCP tools (@mcp.tool() definitions)
└── __init__.py

plugin/
├── mcp_server.lua    # grandMA3 Lua plugin
└── MCP Server.xml    # Plugin configuration
```

## Quick Start

### 1. Install Python Dependencies

```bash
poetry install
```

### 2. Deploy the Lua Plugin to MA3

Copy `.env.example` to `.env` and configure your paths:

```bash
cp .env.example .env
# Edit .env with your MA3 installation path
```

Then deploy:

```bash
./deploy.sh
```

Or manually copy `plugin/mcp_server.lua` to your MA3 plugins folder:
- **macOS**: `~/MALightingTechnology/gma3_X.X.X/shared/resource/lib_plugins/mcp_server/`
- **Windows**: `%USERPROFILE%\MALightingTechnology\gma3_X.X.X\shared\resource\lib_plugins\mcp_server\`

### 3. Start the Plugin in MA3

1. In MA3, go to **Menu → Plugins**
2. Create or select the "MCP Server" plugin
3. Start the plugin (it will poll for commands in the background)

### 4. Configure Your AI Assistant

**For VS Code (GitHub Copilot):**

The workspace settings are already configured. Just open the project in VS Code.

**For Claude Desktop:**

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "grandMA3": {
      "command": "poetry",
      "args": ["run", "python", "-m", "ma3_mcp.server"],
      "cwd": "/path/to/MA3-MCP"
    }
  }
}
```

## Configuration

All configuration is done via environment variables. Copy `.env.example` to `.env`:

```bash
# IPC paths (defaults work for most setups)
MA3_IPC_DIR=/Users/Shared/MA3

# Plugin deployment path
MA3_PLUGIN_DIR=~/MALightingTechnology/gma3_2.3.2/shared/resource/lib_plugins/mcp_server

# OSC reload settings
MA3_OSC_HOST=127.0.0.1
MA3_OSC_PORT=8000
```

### Platform Defaults

| Platform | IPC Directory | 
|----------|---------------|
| macOS    | `/Users/Shared/MA3/` |
| Windows  | `C:/ProgramData/MA3/` |

## Communication Architecture

Uses file-based IPC for reliable cross-process communication:

```
MCP Client (Python)                    grandMA3 (Lua Plugin)
       │                                       │
       ├── Write command ──────────────────────┤
       │   mcp_command.txt                     │
       │                                       ├── Poll & Execute
       │                                       │
       ├── Read response ◄─────────────────────┤
           mcp_response.txt                    │
```

## Available Tools

### Fixture Control
- `ma3_list_fixtures` - List all patched fixtures
- `ma3_select` - Select fixtures by ID, range, or group
- `ma3_set_attribute` - Set attribute on selection
- `ma3_set_color` - Set RGB color on selection
- `ma3_set_position` - Set pan/tilt on selection

### Cue Management
- `ma3_store_cue` - Store cue with timing and name
- `ma3_store_cue_part` - Store cue part for complex timing
- `ma3_set_cue_timing` - Modify existing cue timing
- `ma3_set_cue_trigger` - Set cue trigger mode (Go/Time/Follow)
- `ma3_delete_cue` - Delete a cue
- `ma3_goto_cue` - Jump to a specific cue

### Playback Control
- `ma3_playback` - Control sequence (go, back, off, top)
- `ma3_executor_fader` - Set executor fader level
- `ma3_executor_go` - Trigger executor actions
- `ma3_assign_to_executor` - Assign sequence to executor (with optional name)
- `ma3_label_executor` - Set or change executor label/name

### Inspection Tools
- `ma3_get_sequence_overview` - List all cues in a sequence
- `ma3_get_cue_contents` - Get cue details and timing
- `ma3_get_fixture_status` - Get fixture programmer/output values
- `ma3_list_programmer_detailed` - Detailed programmer contents

### Query Functions
- `ma3_query` - Query any MA3 object
- `ma3_get_property` - Get object property
- `ma3_get_all_properties` - Get all properties as JSON
- `ma3_list_children` - List object children

## Development

### Deploy Changes

Use the deploy script to copy the Lua plugin and reload:

```bash
./deploy.sh
```

This will:
1. Copy `plugin/mcp_server.lua` to MA3
2. Send OSC command to reload the plugin

### VS Code Integration

The project includes VS Code settings for:
- MCP server configuration
- Terminal profiles for MA3 Command Line and System Monitor
- Auto-approve for deploy script

### Plugin Reload Setup

For the deploy script to hot-reload the plugin, you need to configure the plugin correctly in MA3.
See this forum thread for detailed instructions:
- [grandMA3 VSCode Workflow](https://forum.malighting.com/forum/thread/68211-grandma3-vscode-workflow/)

## License

This project is licensed under the [GNU Affero General Public License v3.0](LICENSE) (AGPL-3.0-or-later).

If you run a modified version of this software to provide a service over a network, you must make the complete corresponding source code available to the users of that service.
