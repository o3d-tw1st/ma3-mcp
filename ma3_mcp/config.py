"""
Configuration management for MA3-MCP.

Paths and settings can be configured via:
1. Environment variables (MA3_COMMAND_FILE, MA3_RESPONSE_FILE)
2. .env file in project root
3. Default platform-specific paths
"""

import os
import platform
from pathlib import Path
from typing import Optional

# Try to load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def get_default_ipc_dir() -> Path:
    """Get the default IPC directory based on platform."""
    system = platform.system()
    
    if system == "Darwin":  # macOS
        return Path("/Users/Shared/MA3")
    elif system == "Windows":
        return Path("C:/ProgramData/MA3")
    else:
        raise RuntimeError(f"Unsupported platform: {system}")


def get_ipc_dir() -> Path:
    """Get the IPC directory, respecting environment override."""
    env_dir = os.environ.get("MA3_IPC_DIR")
    if env_dir:
        return Path(env_dir)
    return get_default_ipc_dir()


def get_command_file() -> Path:
    """Get the command file path."""
    env_file = os.environ.get("MA3_COMMAND_FILE")
    if env_file:
        return Path(env_file)
    return get_ipc_dir() / "mcp_command.txt"


def get_response_file() -> Path:
    """Get the response file path."""
    env_file = os.environ.get("MA3_RESPONSE_FILE")
    if env_file:
        return Path(env_file)
    return get_ipc_dir() / "mcp_response.txt"


def get_ma3_plugin_dir() -> Optional[Path]:
    """
    Get the MA3 plugin directory.
    
    This varies by installation, so it must be configured via environment
    variable MA3_PLUGIN_DIR or will return None.
    """
    env_dir = os.environ.get("MA3_PLUGIN_DIR")
    if env_dir:
        return Path(env_dir)
    
    # Try common default locations
    system = platform.system()
    home = Path.home()
    
    if system == "Darwin":  # macOS
        # Check for MALightingTechnology folder in home
        ma_dir = home / "MALightingTechnology"
        if ma_dir.exists():
            # Find the latest gma3 version
            gma3_dirs = sorted(ma_dir.glob("gma3_*"), reverse=True)
            for gma3_dir in gma3_dirs:
                plugin_dir = gma3_dir / "shared/resource/lib_plugins/mcp_server"
                if plugin_dir.parent.exists():
                    return plugin_dir
    elif system == "Windows":
        # Windows default paths (onPC often uses %USERPROFILE%\MALightingTechnology)
        for base in [
            home / "MALightingTechnology",
            Path("C:/ProgramData/MALightingTechnology"),
            home / "Documents/MALightingTechnology",
        ]:
            if base.exists():
                gma3_dirs = sorted(base.glob("gma3_*"), reverse=True)
                for gma3_dir in gma3_dirs:
                    plugin_dir = gma3_dir / "shared/resource/lib_plugins/mcp_server"
                    if plugin_dir.parent.exists():
                        return plugin_dir
    
    return None


# Module-level constants for convenience
COMMAND_FILE = get_command_file()
RESPONSE_FILE = get_response_file()
