"""MA3 File Communication - Direct file-based IPC with grandMA3."""

import time
import uuid
from typing import Optional

from .config import get_command_file, get_response_file


def _ensure_files() -> None:
    """Ensure command and response files exist."""
    command_file = get_command_file()
    response_file = get_response_file()
    
    command_file.parent.mkdir(parents=True, exist_ok=True)
    command_file.touch(exist_ok=True)
    response_file.touch(exist_ok=True)


def send(command: str, timeout: float = 5.0) -> Optional[str]:
    """
    Send a command to grandMA3 and wait for response.
    
    Args:
        command: Command string for the Lua plugin
        timeout: Max wait time in seconds
        
    Returns:
        Response string or None on timeout
    """
    _ensure_files()
    
    command_file = get_command_file()
    response_file = get_response_file()
    
    request_id = str(uuid.uuid4())[:8]
    command_file.write_text(f"{request_id}:{command}")
    
    start = time.time()
    while time.time() - start < timeout:
        try:
            response = response_file.read_text().strip()
            if response.startswith(f"{request_id}:"):
                return response[len(request_id) + 1:]
        except Exception:
            pass
        time.sleep(0.05)
    
    return None


def cmd(command: str) -> Optional[str]:
    """Execute a direct MA3 console command."""
    return send(f"cmd:{command}")


def clear() -> None:
    """Clear command and response files."""
    command_file = get_command_file()
    response_file = get_response_file()
    
    command_file.write_text("")
    response_file.write_text("")