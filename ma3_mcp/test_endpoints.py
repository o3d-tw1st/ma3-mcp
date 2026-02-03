#!/usr/bin/env python3
"""
Interactive Test Script for MA3 MCP Server endpoints.
Runs each test step-by-step, printing full output for visual verification.

Usage:
    python test_endpoints.py          # Interactive mode (press Enter between tests)
    python test_endpoints.py --auto   # Auto mode (no pauses)
    
Requires: MA3 running with MCP plugin active
"""

import sys
import json
from typing import Any

from ma3_mcp.ma3_comm import send, cmd, clear

# Test configuration - ADJUST THESE FOR YOUR SHOW
TEST_FIXTURE_ID = 1             # Fixture ID for single-fixture tests
TEST_FIXTURE_RANGE = "1 Thru 3" # Range for batch tests (dimmers)
TEST_COLOR_RANGE = "401 Thru 403"  # Range for color tests (fixtures with RGB)
TEST_SEQUENCE = 1               # Sequence number for cue tests
TEST_PAGE = 1                   # Page number for executor tests
TEST_EXECUTOR = 201             # Executor number for playback tests
TEST_UNIVERSE = 1               # DMX universe for DMX tests
TEST_GROUP = 17                 # Group number to test selection

# Colors for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

# Global mode
INTERACTIVE = True


def wait_for_user(prompt: str = "Press Enter for next test (or 'q' to quit)...") -> bool:
    """Wait for user input in interactive mode. Returns False if user wants to quit."""
    if not INTERACTIVE:
        return True
    try:
        response = input(f"\n{DIM}{prompt}{RESET}")
        if response.lower() in ('q', 'quit', 'exit'):
            return False
        return True
    except (KeyboardInterrupt, EOFError):
        return False


def print_header(text: str) -> None:
    print(f"\n{BOLD}{CYAN}{'=' * 70}{RESET}")
    print(f"{BOLD}{CYAN}  {text}{RESET}")
    print(f"{BOLD}{CYAN}{'=' * 70}{RESET}")


def print_subheader(text: str) -> None:
    print(f"\n{MAGENTA}--- {text} ---{RESET}")


def print_result(result: Any, indent: int = 2) -> None:
    """Print full result with pretty formatting."""
    prefix = " " * indent
    
    if result is None:
        print(f"{prefix}{YELLOW}(No response - MA3 not connected?){RESET}")
        return
    
    # Try to pretty-print JSON
    if isinstance(result, str):
        try:
            parsed = json.loads(result)
            formatted = json.dumps(parsed, indent=2)
            for line in formatted.split("\n"):
                print(f"{prefix}{line}")
            return
        except json.JSONDecodeError:
            pass
    
    # Print as-is (no truncation)
    result_str = str(result)
    for line in result_str.split("\n"):
        print(f"{prefix}{line}")


def print_test(name: str, command: str, result: Any, success: bool = True) -> None:
    """Print test with command, result, and status."""
    status = f"{GREEN}✓ PASS{RESET}" if success else f"{RED}✗ FAIL{RESET}"
    
    print(f"\n{BOLD}{name}{RESET}")
    print(f"  {DIM}Command:{RESET} {CYAN}{command}{RESET}")
    print(f"  {DIM}Status:{RESET}  {status}")
    print(f"  {DIM}Output:{RESET}")
    print_result(result, indent=4)


def is_error(result: Any) -> bool:
    """Check if result indicates an error."""
    if result is None:
        return True
    if isinstance(result, str):
        if result.startswith("ERR:"):
            return True
        if "Illegal" in result:
            return True
        try:
            parsed = json.loads(result)
            if isinstance(parsed, dict):
                status = parsed.get("status", "").upper()
                if status == "OK":
                    return False
                if status == "FAILED":
                    return True
        except json.JSONDecodeError:
            pass
        lower = result.lower()
        if "error" in lower and "errors" not in lower:
            return True
    return False


def run_tests() -> dict:
    """Run all endpoint tests interactively."""
    results = {"passed": 0, "failed": 0}
    
    # =========================================================================
    print_header("1. CONNECTION TEST")
    # =========================================================================
    
    print_subheader("Testing connection to MA3")
    print("Clearing any stale responses...")
    clear()
    
    command = "listfix:"
    result = send(command)
    success = result is not None and not is_error(result)
    print_test("Connection Check", command, result, success)
    
    if not success:
        print(f"\n{RED}{'=' * 70}")
        print(f"MA3 CONNECTION FAILED!")
        print(f"{'=' * 70}{RESET}")
        print(f"\n{YELLOW}Checklist:{RESET}")
        print("  1. Is grandMA3 running?")
        print("  2. Is the MCP plugin active in the Plugins pool?")
        print("  3. Did you reload the plugin after changes? (ReloadAllPlugins)")
        print("  4. Do files exist at /Users/Shared/MA3/mcp_command.txt?")
        print("\n{DIM}Run: ls -la /Users/Shared/MA3/{RESET}")
        return results
    
    results["passed"] += 1
    if not wait_for_user():
        return results
    
    # =========================================================================
    print_header("2. FIXTURE LISTING")
    # =========================================================================
    
    # List all fixtures
    print_subheader("List all patched fixtures")
    command = "listfix:"
    result = send(command)
    success = not is_error(result)
    print_test("List Fixtures", command, result, success)
    results["passed" if success else "failed"] += 1
    if not wait_for_user():
        return results
    
    # =========================================================================
    print_header("3. FIXTURE ATTRIBUTES")
    # =========================================================================
    
    # List fixture attributes
    print_subheader(f"List attributes for fixture {TEST_FIXTURE_ID}")
    command = f"listattr:{TEST_FIXTURE_ID}"
    result = send(command)
    success = not is_error(result)
    print_test("List Attributes", command, result, success)
    results["passed" if success else "failed"] += 1
    if not wait_for_user():
        return results
    
    # Get specific attribute
    print_subheader(f"Get Dimmer value for fixture {TEST_FIXTURE_ID}")
    command = f"getattr:{TEST_FIXTURE_ID} Dimmer"
    result = send(command)
    success = not is_error(result)
    print_test("Get Attribute", command, result, success)
    results["passed" if success else "failed"] += 1
    if not wait_for_user():
        return results
    
    # =========================================================================
    print_header("4. GROUPS")
    # =========================================================================
    
    print_subheader("List all groups")
    command = "listgroups:"
    result = send(command)
    success = not is_error(result)
    print_test("List Groups", command, result, success)
    results["passed" if success else "failed"] += 1
    if not wait_for_user():
        return results
    
    # =========================================================================
    print_header("5. PROGRAMMER")
    # =========================================================================
    
    print_subheader("List programmer contents (fixtures with values)")
    command = "listprog:"
    result = send(command)
    success = not is_error(result)
    print_test("List Programmer", command, result, success)
    results["passed" if success else "failed"] += 1
    if not wait_for_user():
        return results
    
    print_subheader(f"Get programmer info for fixture {TEST_FIXTURE_ID}")
    command = f"getprog:{TEST_FIXTURE_ID}"
    result = send(command)
    success = not is_error(result)
    print_test("Get Programmer Values", command, result, success)
    results["passed" if success else "failed"] += 1
    if not wait_for_user():
        return results
    
    # =========================================================================
    print_header("6. SELECTION")
    # =========================================================================
    
    print_subheader("Get current selection")
    command = "getselection:"
    result = send(command)
    success = not is_error(result)
    print_test("Get Selection", command, result, success)
    results["passed" if success else "failed"] += 1
    if not wait_for_user():
        return results
    
    print_subheader(f"Select fixtures {TEST_FIXTURE_RANGE}")
    command = f"select:{TEST_FIXTURE_RANGE}"
    result = send(command)
    success = not is_error(result)
    print_test("Select Fixtures", command, result, success)
    print(f"\n  {YELLOW}➜ Check MA3: Are fixtures {TEST_FIXTURE_RANGE} selected?{RESET}")
    results["passed" if success else "failed"] += 1
    if not wait_for_user():
        return results
    
    print_subheader(f"Select Group {TEST_GROUP}")
    command = f"select:Group {TEST_GROUP}"
    result = send(command)
    success = not is_error(result)
    print_test("Select Group", command, result, success)
    print(f"\n  {YELLOW}➜ Check MA3: Are Group {TEST_GROUP} fixtures selected?{RESET}")
    results["passed" if success else "failed"] += 1
    if not wait_for_user():
        return results
    
    print_subheader("Clear selection")
    command = "select:Clear"
    result = send(command)
    success = not is_error(result)
    print_test("Clear Selection", command, result, success)
    print(f"\n  {YELLOW}➜ Check MA3: Is selection empty?{RESET}")
    results["passed" if success else "failed"] += 1
    if not wait_for_user():
        return results
    
    # =========================================================================
    print_header("7. ATTRIBUTE CONTROL")
    # =========================================================================
    
    print_subheader(f"Select fixtures {TEST_FIXTURE_RANGE}")
    command = f"select:{TEST_FIXTURE_RANGE}"
    result = send(command)
    print_test("Select for Dimmer Test", command, result, not is_error(result))
    
    print_subheader("Set Dimmer to 50%")
    command = "setattr:Dimmer 50"
    result = send(command)
    success = not is_error(result)
    print_test("Set Dimmer", command, result, success)
    print(f"\n  {YELLOW}➜ Check MA3: Are fixtures at 50%?{RESET}")
    results["passed" if success else "failed"] += 1
    if not wait_for_user():
        return results
    
    print_subheader("Set Dimmer to 100%")
    command = "setattr:Dimmer 100"
    result = send(command)
    success = not is_error(result)
    print_test("Set Dimmer Full", command, result, success)
    print(f"\n  {YELLOW}➜ Check MA3: Are fixtures at 100%?{RESET}")
    results["passed" if success else "failed"] += 1
    if not wait_for_user():
        return results
    
    # =========================================================================
    print_header("8. COLOR CONTROL")
    # =========================================================================
    
    print_subheader(f"Select color fixtures {TEST_COLOR_RANGE}")
    command = f"select:{TEST_COLOR_RANGE}"
    result = send(command)
    print_test("Select Color Fixtures", command, result, not is_error(result))
    
    print_subheader("Set color to Red (100, 0, 0)")
    command = "setcolor:100 0 0"
    result = send(command)
    success = not is_error(result)
    print_test("Set Color Red", command, result, success)
    print(f"\n  {YELLOW}➜ Check MA3: Are fixtures RED?{RESET}")
    results["passed" if success else "failed"] += 1
    if not wait_for_user():
        return results
    
    print_subheader("Set color to Blue (0, 0, 100)")
    command = "setcolor:0 0 100"
    result = send(command)
    success = not is_error(result)
    print_test("Set Color Blue", command, result, success)
    print(f"\n  {YELLOW}➜ Check MA3: Are fixtures BLUE?{RESET}")
    results["passed" if success else "failed"] += 1
    if not wait_for_user():
        return results
    
    print_subheader("Set color to White (100, 100, 100)")
    command = "setcolor:100 100 100"
    result = send(command)
    success = not is_error(result)
    print_test("Set Color White", command, result, success)
    print(f"\n  {YELLOW}➜ Check MA3: Are fixtures WHITE?{RESET}")
    results["passed" if success else "failed"] += 1
    if not wait_for_user():
        return results
    
    # =========================================================================
    print_header("9. CLEAR PROGRAMMER")
    # =========================================================================
    
    print_subheader("Clear All (via cmd:)")
    command = "ClearAll"
    result = cmd(command)
    success = not is_error(result)
    print_test("ClearAll", f"cmd:{command}", result, success)
    print(f"\n  {YELLOW}➜ Check MA3: Is programmer empty?{RESET}")
    results["passed" if success else "failed"] += 1
    if not wait_for_user():
        return results
    
    # =========================================================================
    print_header("10. SEQUENCES & CUES")
    # =========================================================================
    
    print_subheader(f"Get current cue for Sequence {TEST_SEQUENCE}")
    command = f"getcue:{TEST_SEQUENCE}"
    result = send(command)
    success = not is_error(result)
    print_test("Get Current Cue", command, result, success)
    results["passed" if success else "failed"] += 1
    if not wait_for_user():
        return results
    
    print_subheader(f"Get sequence status for Sequence {TEST_SEQUENCE}")
    command = f"seqstatus:{TEST_SEQUENCE}"
    result = send(command)
    success = not is_error(result)
    print_test("Get Sequence Status", command, result, success)
    results["passed" if success else "failed"] += 1
    if not wait_for_user():
        return results
    
    # =========================================================================
    print_header("11. EXECUTORS")
    # =========================================================================
    
    print_subheader(f"List executors on Page {TEST_PAGE}")
    command = f"listexec:{TEST_PAGE}"
    result = send(command)
    success = not is_error(result)
    print_test("List Executors", command, result, success)
    results["passed" if success else "failed"] += 1
    if not wait_for_user():
        return results
    
    # =========================================================================
    print_header("12. EXECUTOR CONTROL")
    # =========================================================================
    
    print_subheader(f"Set executor fader to 50% (Page {TEST_PAGE}.{TEST_EXECUTOR})")
    command = f"execfader:{TEST_PAGE}.{TEST_EXECUTOR} 50"
    result = send(command)
    success = not is_error(result)
    print_test("Set Executor Fader 50%", command, result, success)
    print(f"\n  {YELLOW}➜ Check MA3: Is Exec {TEST_PAGE}.{TEST_EXECUTOR} at 50%?{RESET}")
    results["passed" if success else "failed"] += 1
    if not wait_for_user():
        return results
    
    print_subheader(f"Set executor fader to 100% (Page {TEST_PAGE}.{TEST_EXECUTOR})")
    command = f"execfader:{TEST_PAGE}.{TEST_EXECUTOR} 100"
    result = send(command)
    success = not is_error(result)
    print_test("Set Executor Fader 100%", command, result, success)
    print(f"\n  {YELLOW}➜ Check MA3: Is Exec {TEST_PAGE}.{TEST_EXECUTOR} at 100%?{RESET}")
    results["passed" if success else "failed"] += 1
    if not wait_for_user():
        return results
    
    print_subheader(f"Executor GO (Page {TEST_PAGE}.{TEST_EXECUTOR})")
    command = f"execgo:{TEST_PAGE}.{TEST_EXECUTOR} go"
    result = send(command)
    success = not is_error(result)
    print_test("Executor GO", command, result, success)
    print(f"\n  {YELLOW}➜ Check MA3: Did sequence advance?{RESET}")
    results["passed" if success else "failed"] += 1
    if not wait_for_user():
        return results
    
    print_subheader(f"Executor OFF (Page {TEST_PAGE}.{TEST_EXECUTOR})")
    command = f"execgo:{TEST_PAGE}.{TEST_EXECUTOR} off"
    result = send(command)
    success = not is_error(result)
    print_test("Executor OFF", command, result, success)
    print(f"\n  {YELLOW}➜ Check MA3: Is executor off?{RESET}")
    results["passed" if success else "failed"] += 1
    if not wait_for_user():
        return results
    
    # =========================================================================
    print_header("13. OBJECT QUERIES")
    # =========================================================================
    
    print_subheader("Query DataPool object")
    command = "?DataPool"
    result = send(command)
    success = not is_error(result)
    print_test("Query Object", command, result, success)
    results["passed" if success else "failed"] += 1
    if not wait_for_user():
        return results
    
    print_subheader(f"Query Sequence {TEST_SEQUENCE}")
    command = f"?Sequence {TEST_SEQUENCE}"
    result = send(command)
    success = not is_error(result)
    print_test("Query Sequence", command, result, success)
    results["passed" if success else "failed"] += 1
    if not wait_for_user():
        return results
    
    print_subheader(f"Get property: Sequence {TEST_SEQUENCE}.name")
    command = f"get:Sequence {TEST_SEQUENCE}.name"
    result = send(command)
    success = not is_error(result)
    print_test("Get Property", command, result, success)
    results["passed" if success else "failed"] += 1
    if not wait_for_user():
        return results
    
    print_subheader("List children of DataPool")
    command = "children:DataPool"
    result = send(command)
    success = not is_error(result)
    print_test("List Children", command, result, success)
    results["passed" if success else "failed"] += 1
    if not wait_for_user():
        return results
    
    # =========================================================================
    print_header("14. DIRECT COMMANDS")
    # =========================================================================
    
    print_subheader("Run MA3 command via cmd:")
    command = f"Fixture {TEST_FIXTURE_ID}"
    result = cmd(command)
    success = not is_error(result)
    print_test("Direct Command (select fixture)", f"cmd:{command}", result, success)
    print(f"\n  {YELLOW}➜ Check MA3: Is fixture {TEST_FIXTURE_ID} selected?{RESET}")
    results["passed" if success else "failed"] += 1
    if not wait_for_user():
        return results
    
    print_subheader("Run ClearAll via cmd:")
    command = "ClearAll"
    result = cmd(command)
    success = not is_error(result)
    print_test("Direct Command (ClearAll)", f"cmd:{command}", result, success)
    results["passed" if success else "failed"] += 1
    if not wait_for_user():
        return results
    
    # =========================================================================
    print_header("15. DMX READING")
    # =========================================================================
    
    print_subheader(f"Get DMX value at address 1, universe {TEST_UNIVERSE}")
    command = f"getdmx:1 {TEST_UNIVERSE}"
    result = send(command)
    success = not is_error(result)
    print_test("Get DMX Value", command, result, success)
    results["passed" if success else "failed"] += 1
    if not wait_for_user():
        return results
    
    print_subheader(f"Get all non-zero DMX in universe {TEST_UNIVERSE}")
    command = f"dmxuni:{TEST_UNIVERSE}"
    result = send(command)
    success = not is_error(result)
    print_test("Get DMX Universe", command, result, success)
    results["passed" if success else "failed"] += 1
    if not wait_for_user():
        return results
    
    # =========================================================================
    print_header("16. CUE STORAGE WITH FADE & DELAY")
    # =========================================================================
    
    print_subheader("Set up fixtures for cue storage")
    send(f"select:{TEST_FIXTURE_RANGE}")
    send("setattr:Dimmer 75")
    result = send("getselection:")
    print_test("Select & Set Dimmer", f"select:{TEST_FIXTURE_RANGE} + setattr:Dimmer 75", result, not is_error(result))
    print(f"\n  {YELLOW}➜ Check MA3: Fixtures at 75%?{RESET}")
    if not wait_for_user():
        return results
    
    # MA3 syntax: Store Cue X CueFade "Y" CueDelay "Z" /NoConfirmation
    print_subheader("Store Cue 99.9 with CueFade 3s and CueDelay 1s")
    command = 'Store Cue 99.9 CueFade "3" CueDelay "1" /NC'
    result = cmd(command)
    success = not is_error(result)
    print_test("Store Cue with Fade+Delay", f"cmd:{command}", result, success)
    print(f"\n  {YELLOW}➜ Check MA3: Cue 99.9 stored with Fade 3s, Delay 1s?{RESET}")
    print(f"  {DIM}Open Sequence sheet to verify timing values{RESET}")
    results["passed" if success else "failed"] += 1
    if not wait_for_user():
        return results
    
    print_subheader("Clear programmer")
    cmd("ClearAll")
    
    print_subheader("Off the sequence first")
    cmd("Off Sequence 1")
    
    print_subheader("Goto Cue 99.9 (should delay 1s then fade 3s)")
    command = "Goto Cue 99.9"
    result = cmd(command)
    success = not is_error(result)
    print_test("Goto Cue", f"cmd:{command}", result, success)
    print(f"\n  {YELLOW}➜ Check MA3: 1s delay, then 3s fade to 75%?{RESET}")
    results["passed" if success else "failed"] += 1
    if not wait_for_user():
        return results
    
    print_subheader("Delete test cue")
    command = "Delete Cue 99.9 /NC"
    result = cmd(command)
    success = not is_error(result)
    print_test("Delete Cue", f"cmd:{command}", result, success)
    results["passed" if success else "failed"] += 1
    if not wait_for_user():
        return results
    
    # =========================================================================
    print_header("17. CUE TRIGGER MODES (Follow & Time)")
    # =========================================================================
    
    # Note about cue naming best practices
    print(f"\n  {BOLD}{YELLOW}💡 Best Practice: Always name cues descriptively!{RESET}")
    print(f"  {DIM}Examples: 'Intro', 'Verse 1', 'Chorus Bump', 'Blackout'{RESET}")
    print(f"  {DIM}This helps identify cues in sequence sheets and during playback.{RESET}\n")
    
    print_subheader("Create test cues for trigger mode demo")
    
    # First, set up some fixture values
    send(f"select:{TEST_FIXTURE_RANGE}")
    send("setattr:Dimmer 50")
    
    # Store Cue 90.1 (base cue)
    # MA3 syntax: Store Cue X "Name" CueFade "Y" /NC
    command = 'Store Cue 90.1 "Act1-Open" CueFade "2" /NC'
    result = cmd(command)
    print_test("Store Cue 90.1 'Act1-Open'", f"cmd:{command}", result, not is_error(result))
    
    # Change values for second cue
    send("setattr:Dimmer 100")
    
    # Store Cue 90.2 with Trigger Type = Time (auto-trigger after X seconds)
    # First store the cue, then set the trigger type
    command = 'Store Cue 90.2 "Act1-Build" CueFade "1" /NC'
    result = cmd(command)
    print_test("Store Cue 90.2 'Act1-Build'", f"cmd:{command}", result, not is_error(result))
    
    # Set trigger type to "Time" with 2 seconds
    # MA3 syntax: Set Cue X Property "TrigType" "Time"
    # MA3 syntax: Set Cue X Property "TrigTime" "2"
    command = 'Set Cue 90.2 Property "TrigType" "Time"'
    result = cmd(command)
    print_test("Set TrigType = Time", f"cmd:{command}", result, not is_error(result))
    
    command = 'Set Cue 90.2 Property "TrigTime" "2"'
    result = cmd(command)
    print_test("Set TrigTime = 2s", f"cmd:{command}", result, not is_error(result))
    
    # Change values for third cue
    send("setattr:Dimmer 0")
    
    # Store Cue 90.3 with Trigger Type = Follow (auto-trigger after previous cue finishes)
    command = 'Store Cue 90.3 "Act1-Blackout" CueFade "3" /NC'
    result = cmd(command)
    print_test("Store Cue 90.3 'Act1-Blackout'", f"cmd:{command}", result, not is_error(result))
    
    # Set trigger type to "Follow"
    command = 'Set Cue 90.3 Property "TrigType" "Follow"'
    result = cmd(command)
    print_test("Set TrigType = Follow", f"cmd:{command}", result, not is_error(result))
    
    print(f"\n  {YELLOW}➜ Check MA3 Sequence Sheet:{RESET}")
    print(f"  {DIM}• Cue 90.1 'Act1-Open':     Trig=Go (default){RESET}")
    print(f"  {DIM}• Cue 90.2 'Act1-Build':    Trig=Time, TrigTime=2s{RESET}")
    print(f"  {DIM}• Cue 90.3 'Act1-Blackout': Trig=Follow{RESET}")
    results["passed" if not is_error(result) else "failed"] += 1
    if not wait_for_user():
        return results
    
    print_subheader("Play trigger mode demo")
    cmd("ClearAll")
    cmd("Off Sequence 1")
    
    command = "Goto Cue 90.1"
    result = cmd(command)
    print_test("Goto Cue 90.1 (triggers chain)", f"cmd:{command}", result, not is_error(result))
    print(f"\n  {YELLOW}➜ Watch MA3:{RESET}")
    print(f"  {DIM}1. Cue 90.1: Fade in 2s to 50%{RESET}")
    print(f"  {DIM}2. After 2s wait: Cue 90.2 auto-triggers (Time), fade 1s to 100%{RESET}")
    print(f"  {DIM}3. When 90.2 done: Cue 90.3 auto-triggers (Follow), fade 3s to 0%{RESET}")
    results["passed" if not is_error(result) else "failed"] += 1
    if not wait_for_user():
        return results
    
    print_subheader("Delete trigger mode test cues")
    cmd("Delete Cue 90.1 Thru 90.3 /NC")
    print(f"  {DIM}Deleted test cues 90.1-90.3{RESET}")
    if not wait_for_user():
        return results
    
    # =========================================================================
    print_header("18. CUE PARTS (Different Timings per Fixture/Attribute)")
    # =========================================================================
    
    print(f"\n  {BOLD}{YELLOW}💡 Cue Parts allow different fade times within the same cue!{RESET}")
    print(f"  {DIM}Use cases:{RESET}")
    print(f"  {DIM}• Different fade times for different fixture groups{RESET}")
    print(f"  {DIM}• Delayed color change while dimmer stays constant{RESET}")
    print(f"  {DIM}• Complex scene builds with staggered timing{RESET}\n")
    
    print_subheader("Create cue with multiple parts (different timings)")
    
    # Store main cue with dimmers (Part 0 - default)
    send(f"select:{TEST_FIXTURE_RANGE}")
    send("setattr:Dimmer 80")
    
    # Store Cue 91.1 Part 0 (main cue part with dimmer)
    command = 'Store Cue 91.1 "MultiPart-Demo" CueFade "1" /NC'
    result = cmd(command)
    print_test("Store Cue 91.1 Part 0 (dimmer)", f"cmd:{command}", result, not is_error(result))
    
    # Select color fixtures and store in Part 1 with different timing
    if TEST_COLOR_RANGE != TEST_FIXTURE_RANGE:
        send(f"select:{TEST_COLOR_RANGE}")
        send("setcolor:100 0 0")  # Red
    
    # Store Part 1 with longer fade time for color
    # MA3 syntax: Store Cue X Part Y CueFade "Z" /NC
    command = 'Store Cue 91.1 Part 1 "Color-Slow" CueFade "5" /NC'
    result = cmd(command)
    print_test("Store Cue 91.1 Part 1 (color, 5s fade)", f"cmd:{command}", result, not is_error(result))
    
    # Store Part 2 with delay for additional effect
    send(f"select:{TEST_FIXTURE_RANGE}")
    send("setattr:Dimmer 100")
    
    command = 'Store Cue 91.1 Part 2 "Dimmer-Delayed" CueFade "2" CueDelay "3" /NC'
    result = cmd(command)
    print_test("Store Cue 91.1 Part 2 (dimmer delayed)", f"cmd:{command}", result, not is_error(result))
    
    print(f"\n  {YELLOW}➜ Check MA3 Sequence Sheet (expand cue 91.1):{RESET}")
    print(f"  {DIM}• Part 0: Dimmer, 1s fade{RESET}")
    print(f"  {DIM}• Part 1 'Color-Slow': Color, 5s fade{RESET}")
    print(f"  {DIM}• Part 2 'Dimmer-Delayed': Dimmer, 3s delay + 2s fade{RESET}")
    results["passed" if not is_error(result) else "failed"] += 1
    if not wait_for_user():
        return results
    
    print_subheader("Play cue parts demo")
    cmd("ClearAll")
    cmd("Off Sequence 1")
    
    command = "Goto Cue 91.1"
    result = cmd(command)
    print_test("Goto Cue 91.1 (multi-part)", f"cmd:{command}", result, not is_error(result))
    print(f"\n  {YELLOW}➜ Watch MA3:{RESET}")
    print(f"  {DIM}• Part 0: Dimmer immediately starts 1s fade{RESET}")
    print(f"  {DIM}• Part 1: Color slowly fades over 5s{RESET}")
    print(f"  {DIM}• Part 2: After 3s delay, dimmer fades 2s more{RESET}")
    results["passed" if not is_error(result) else "failed"] += 1
    if not wait_for_user():
        return results
    
    print_subheader("Delete cue parts test")
    cmd("Delete Cue 91.1 /NC")
    print(f"  {DIM}Deleted test cue 91.1 (all parts){RESET}")
    if not wait_for_user():
        return results
    
    # =========================================================================
    print_header("19. IN/OUT FADE TIMES (Split Timing)")
    # =========================================================================
    
    print(f"\n  {BOLD}{YELLOW}💡 In/Out fades control dimmer up vs dimmer down separately!{RESET}")
    print(f"  {DIM}CueFade syntax: InFade/OutFade (e.g., '3/7' = 3s in, 7s out){RESET}\n")
    
    print_subheader("Store cue with different In/Out fades")
    
    send(f"select:{TEST_FIXTURE_RANGE}")
    send("setattr:Dimmer 100")
    
    # Store cue with split timing: 1s fade in, 5s fade out
    command = 'Store Cue 92.1 "SplitFade-Demo" CueFade "1/5" /NC'
    result = cmd(command)
    print_test("Store Cue 92.1 (InFade=1s, OutFade=5s)", f"cmd:{command}", result, not is_error(result))
    
    send("setattr:Dimmer 0")
    command = 'Store Cue 92.2 "Slow-Out" CueFade "1/5" /NC'
    result = cmd(command)
    print_test("Store Cue 92.2 (blackout)", f"cmd:{command}", result, not is_error(result))
    
    print(f"\n  {YELLOW}➜ Check MA3 Sequence Sheet:{RESET}")
    print(f"  {DIM}• CueIn Fade = 1s (dimmer going UP){RESET}")
    print(f"  {DIM}• CueOut Fade = 5s (dimmer going DOWN){RESET}")
    results["passed" if not is_error(result) else "failed"] += 1
    if not wait_for_user():
        return results
    
    print_subheader("Demo split fade timing")
    cmd("ClearAll")
    cmd("Off Sequence 1")
    
    result = cmd("Goto Cue 92.1")
    print_test("Goto Cue 92.1 (1s fade UP)", "cmd:Goto Cue 92.1", result, not is_error(result))
    print(f"\n  {YELLOW}➜ Watch: Dimmer fades UP in 1 second{RESET}")
    if not wait_for_user():
        return results
    
    result = cmd("Go+ Sequence 1")
    print_test("Go+ (5s fade DOWN)", "cmd:Go+ Sequence 1", result, not is_error(result))
    print(f"\n  {YELLOW}➜ Watch: Dimmer fades DOWN in 5 seconds (slow out){RESET}")
    results["passed" if not is_error(result) else "failed"] += 1
    if not wait_for_user():
        return results
    
    print_subheader("Delete split fade test cues")
    cmd("Delete Cue 92.1 Thru 92.2 /NC")
    print(f"  {DIM}Deleted test cues 92.1-92.2{RESET}")
    
    print_subheader("Final cleanup")
    cmd("ClearAll")
    cmd("Off Sequence 1")
    print(f"  {DIM}Cleaned up programmer and sequence{RESET}")
    if not wait_for_user():
        return results
    
    # =========================================================================
    print_header("20. INSPECTION & VERIFICATION TOOLS")
    # =========================================================================
    
    print(f"\n  {BOLD}{YELLOW}💡 These tools help verify what's stored in cues and programmer!{RESET}")
    print(f"  {DIM}Use before/after storing to catch programming errors{RESET}\n")
    
    print_subheader("Detailed Programmer Contents")
    
    # Set up some values in programmer
    send(f"select:{TEST_FIXTURE_RANGE}")
    send("setattr:Dimmer 75")
    send("setattr:Pan 25")
    
    result = send("progdetail:")
    print_test("Get detailed programmer", "progdetail:", result, 
               "fixtures" in str(result) or "attributes" in str(result))
    
    try:
        data = json.loads(result)
        if data.get("fixtures"):
            print(f"  {CYAN}Found {data.get('total_fixtures', 0)} fixtures with {data.get('total_attributes', 0)} attributes{RESET}")
            for fix in data.get("fixtures", [])[:2]:  # Show first 2
                print(f"  {DIM}  • {fix.get('name', 'Unknown')}: {fix.get('attributes', {})}{RESET}")
        results["passed"] += 1
    except (json.JSONDecodeError, TypeError):
        print(f"  {YELLOW}Could not parse JSON response{RESET}")
        results["failed"] += 1
    
    if not wait_for_user():
        return results
    
    print_subheader("Store and inspect cue")
    
    # Store a cue for inspection
    result = cmd('Store Cue 93.1 "InspectionTest" CueFade "2" /NC')
    print_test("Store Cue 93.1 for inspection", "cmd:Store Cue 93.1...", result, not is_error(result))
    
    # Get cue contents
    result = send("cuecontents:93.1 1")
    print_test("Get cue 93.1 contents", "cuecontents:93.1 1", result, 
               "cue" in str(result).lower() or "name" in str(result).lower())
    
    try:
        data = json.loads(result)
        print(f"  {CYAN}Cue: {data.get('cue')}, Name: {data.get('name', 'unnamed')}{RESET}")
        if data.get("fade_in"):
            print(f"  {DIM}  Fade In: {data.get('fade_in')}{RESET}")
        if data.get("trigger_type"):
            print(f"  {DIM}  Trigger: {data.get('trigger_type')}{RESET}")
        results["passed"] += 1
    except (json.JSONDecodeError, TypeError):
        print(f"  {YELLOW}Could not parse JSON response{RESET}")
        results["failed"] += 1
    
    if not wait_for_user():
        return results
    
    print_subheader("Sequence Overview")
    
    result = send(f"seqoverview:{TEST_SEQUENCE}")
    print_test(f"Get sequence {TEST_SEQUENCE} overview", f"seqoverview:{TEST_SEQUENCE}", result,
               "cues" in str(result).lower() or "sequence" in str(result).lower())
    
    try:
        data = json.loads(result)
        print(f"  {CYAN}Sequence: {data.get('sequence')}, Name: {data.get('name', 'unnamed')}{RESET}")
        print(f"  {DIM}  Cue count: {data.get('cue_count', len(data.get('cues', [])))}{RESET}")
        if data.get("cues"):
            print(f"  {DIM}  First few cues:{RESET}")
            for cue in data.get("cues", [])[:3]:
                print(f"  {DIM}    • Cue {cue.get('cue')}: {cue.get('name', 'unnamed')} (fade: {cue.get('fade_in', '?')}){RESET}")
        results["passed"] += 1
    except (json.JSONDecodeError, TypeError):
        print(f"  {YELLOW}Could not parse JSON response{RESET}")
        results["failed"] += 1
    
    if not wait_for_user():
        return results
    
    print_subheader("Fixture Status")
    
    result = send(f"fixstatus:{TEST_FIXTURE_ID}")
    print_test(f"Get fixture {TEST_FIXTURE_ID} status", f"fixstatus:{TEST_FIXTURE_ID}", result,
               "fixture_id" in str(result).lower() or "output" in str(result).lower())
    
    try:
        data = json.loads(result)
        print(f"  {CYAN}Fixture: {data.get('name', 'ID ' + str(data.get('fixture_id')))}{RESET}")
        print(f"  {DIM}  Patch: {data.get('patch', 'unknown')}{RESET}")
        print(f"  {DIM}  Selected: {data.get('selected', False)}{RESET}")
        print(f"  {DIM}  In Programmer: {data.get('in_programmer', False)}{RESET}")
        if data.get("output_values"):
            print(f"  {DIM}  Output values: {data.get('output_values')}{RESET}")
        results["passed"] += 1
    except (json.JSONDecodeError, TypeError):
        print(f"  {YELLOW}Could not parse JSON response{RESET}")
        results["failed"] += 1
    
    if not wait_for_user():
        return results
    
    print_subheader("Cleanup inspection test")
    cmd("Delete Cue 93.1 /NC")
    cmd("ClearAll")
    print(f"  {DIM}Deleted test cue 93.1{RESET}")

    return results


def main():
    global INTERACTIVE
    
    if "--auto" in sys.argv:
        INTERACTIVE = False
    
    print(f"\n{BOLD}{'=' * 70}")
    print(f"  MA3 MCP Server - Interactive Endpoint Test")
    print(f"{'=' * 70}{RESET}")
    print(f"\n{DIM}Mode:{RESET} {'Interactive (Enter = next, q = quit)' if INTERACTIVE else 'Automatic'}")
    print(f"\n{DIM}Test Configuration:{RESET}")
    print(f"  Fixture ID:      {CYAN}{TEST_FIXTURE_ID}{RESET}")
    print(f"  Fixture Range:   {CYAN}{TEST_FIXTURE_RANGE}{RESET}")
    print(f"  Color Range:     {CYAN}{TEST_COLOR_RANGE}{RESET}")
    print(f"  Sequence:        {CYAN}{TEST_SEQUENCE}{RESET}")
    print(f"  Page.Executor:   {CYAN}{TEST_PAGE}.{TEST_EXECUTOR}{RESET}")
    print(f"  Test Group:      {CYAN}{TEST_GROUP}{RESET}")
    print(f"  Universe:        {CYAN}{TEST_UNIVERSE}{RESET}")
    
    print(f"\n{YELLOW}Adjust TEST_* variables at top of file for your show!{RESET}")
    
    if INTERACTIVE:
        if not wait_for_user("Press Enter to start tests..."):
            print("\nAborted.")
            return 0
    
    results = run_tests()
    
    # Summary
    print_header("TEST SUMMARY")
    total = results["passed"] + results["failed"]
    
    print(f"\n  {GREEN}Passed:{RESET}  {results['passed']}")
    print(f"  {RED}Failed:{RESET}  {results['failed']}")
    print(f"  {DIM}Total:{RESET}   {total}")
    
    if total > 0:
        pct = (results["passed"] / total) * 100
        color = GREEN if pct >= 80 else YELLOW if pct >= 50 else RED
        print(f"\n  {color}Success rate: {pct:.1f}%{RESET}")
    
    print(f"\n{DIM}Tip: Run with --auto for non-interactive mode{RESET}")
    
    return 0 if results["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
