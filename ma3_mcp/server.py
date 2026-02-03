"""MCP Server for grandMA3 control."""

from mcp.server.fastmcp import FastMCP
from ma3_mcp.ma3_comm import send, cmd

mcp = FastMCP(
    "grandMA3",
    instructions="""
    Control grandMA3 lighting console via MCP.
    
    Available operations:
    - Execute MA3 commands (fixtures, sequences, cues, playback)
    - Set fixture attributes (dimmer, color, position, beam, gobo)
    - Query fixtures, attributes, and programmer values
    - Store and manage cues in sequences
    - Read DMX output values
    
    The MA3 console must be running with the MCP plugin active.
    Use /NC flag with Store and Delete commands to avoid popups.
    """,
)


# =============================================================================
# Command Execution
# =============================================================================


@mcp.tool()
def ma3_command(command: str) -> str:
    """
    Execute any grandMA3 console command.

    Syntax examples:
    - "Fixture 1 At 50" - Set fixture 1 dimmer to 50%
    - "Fixture 1 Thru 10 At Full" - Range of fixtures to 100%
    - "Group 1 At 50" - Control a group
    - "Store Cue 1 /NC" - Store cue (no confirmation)
    - "Go+ Sequence 1" - Next cue
    - "Assign Sequence 1 At Page 1.201" - Assign to executor
    - "Label Page 1.201 \"Main Show\"" - Name an executor
    - "Delete Cue 5 /NC" - Delete cue
    - "Copy Cue 1 At Cue 10 /NC" - Copy cue
    - "Move Cue 2 At Cue 5 /NC" - Move cue
    - "Update Cue 1 /NC" - Update cue with programmer
    - "Store Group 1 \"All Movers\" /NC" - Store selection as group
    - "Off Executor 1.201" - Turn off executor
    - "Clear" - Clear programmer
    - "ClearAll" - Clear programmer and selection
    - "Blind" / "Blind Off" - Toggle blind mode
    - "Highlight" / "Highlight Off" - Toggle highlight
    - "Park Fixture 1" / "Unpark Fixture 1" - Park/unpark
    - "Freeze Executor 1.201" / "Unfreeze" - Freeze executor
    - "BlackOut" / "BlackOut Off" - Master blackout
    - "Store Preset 1.1 \"Color Red\" /NC" - Store preset
    - "Call Preset 1.1" - Apply preset to selection
    - "Stomp" - Remove active values from programmer
    - "Oops" - Undo last action

    Common flags:
    - /NC - No Confirmation (skip popup)
    - /Merge - Merge into existing
    - /Overwrite - Overwrite existing

    Args:
        command: The MA3 command string

    Returns:
        "Ok" on success, error message on failure
    """
    return cmd(command) or "Command executed"


# =============================================================================
# Fixture Management
# =============================================================================


@mcp.tool()
def ma3_list_fixtures() -> str:
    """List all patched fixtures with IDs, names, and patch addresses."""
    return send("listfix:") or "No fixtures found"


@mcp.tool()
def ma3_list_attributes(fixture_id: int) -> str:
    """
    List all attributes of a fixture.

    Args:
        fixture_id: The fixture ID (FID)

    Returns:
        JSON with available attributes (Dimmer, Pan, Tilt, ColorRGB_R, etc.)
    """
    return send(f"listattr:{fixture_id}") or f"Could not get attributes for fixture {fixture_id}"


@mcp.tool()
def ma3_get_attribute(fixture_id: int, attribute: str) -> str:
    """
    Get detailed attribute data including programmer values.

    Args:
        fixture_id: The fixture ID (FID)
        attribute: Attribute name (e.g., "Dimmer", "Pan", "ColorRGB_R")

    Returns:
        JSON with attribute data, programmer value in "programmer.step1.absolute"
    """
    return send(f"getattr:{fixture_id} {attribute}") or f"Could not get {attribute}"


@mcp.tool()
def ma3_get_fixture_value(fixture_id: int, attribute: str) -> str:
    """
    Get current programmer value of a fixture attribute.

    Args:
        fixture_id: The fixture ID (FID)
        attribute: Attribute name

    Returns:
        Value as percentage, or "Not in programmer"
    """
    result = send(f"getprog:{fixture_id} {attribute}")
    return result or "Not in programmer"


@mcp.tool()
def ma3_set_attribute_single(fixture_id: int, attribute: str, value: float) -> str:
    """
    Set attribute on a SINGLE fixture (selects it first).
    
    For multiple fixtures, use ma3_select() + ma3_set_attribute() instead.
    
    Args:
        fixture_id: The fixture ID (FID)
        attribute: Attribute name
        value: Value (0-100)
    """
    cmd(f"ClearSelection")
    cmd(f"Fixture {fixture_id}")
    return send(f"setattr:{attribute} {value}") or "Failed"


@mcp.tool()
def ma3_list_groups() -> str:
    """
    List all fixture groups in the show.
    
    Groups are the most efficient way to select fixtures.
    Use group names with ma3_select() for batch operations.
    """
    return send("listgroups:") or "No groups found"


# =============================================================================
# Programmer & Selection
# =============================================================================


@mcp.tool()
def ma3_get_selection() -> str:
    """
    Get currently selected fixtures.
    
    IMPORTANT: All attribute operations (set_attribute, set_color, etc.) 
    work on the current SELECTION. Always check selection before modifying!
    
    Returns:
        JSON with selected fixtures
    """
    return send("getselection:") or "No selection"


@mcp.tool()
def ma3_select(fixture_spec: str) -> str:
    """
    Select fixtures, REPLACING the current selection.
    
    Use this before set_attribute/set_color to ensure only intended fixtures are modified.
    
    Args:
        fixture_spec: What to select:
            - "1" or "1 Thru 10" - fixture IDs
            - "Group 1" or "Group 17" - group by number (RECOMMENDED)
            - "Group \"ALL MAC\"" - group by name (use quotes)
            - "Clear" - clear selection
    
    NOTE: Group selection by NUMBER is more reliable than by name.
    Use ma3_list_groups() to find group numbers.
    
    Examples:
        ma3_select("1 Thru 5")
        ma3_select("Group 17")        # By number (preferred)
        ma3_select("Group \"ALL MAC\"")  # By name (needs quotes)
        ma3_select("Clear")
    """
    return send(f"select:{fixture_spec}") or "Selection changed"


@mcp.tool()
def ma3_list_programmer() -> str:
    """
    List all fixtures and values currently in the programmer.
    
    Shows what will be stored when you call store_cue.
    """
    return send("listprog:") or "Programmer is empty"


@mcp.tool()
def ma3_clear_programmer() -> str:
    """Clear the programmer and selection (ClearAll)."""
    return cmd("ClearAll") or "Programmer cleared"


@mcp.tool()
def ma3_set_attribute(attribute: str, value: float) -> str:
    """
    Set an attribute on the CURRENTLY SELECTED fixtures.
    
    IMPORTANT: Uses current selection! Call ma3_select() first if needed.
    
    Args:
        attribute: Attribute name (Dimmer, Pan, Tilt, ColorRGB_R, etc.)
        value: Value to set (0-100)
    
    Example workflow:
        1. ma3_select("Group ALL MAC")  # Select fixtures
        2. ma3_set_attribute("Dimmer", 50)  # Set dimmer on selection
    """
    return send(f"setattr:{attribute} {value}") or "Failed"


@mcp.tool()
def ma3_set_color(red: float, green: float, blue: float) -> str:
    """
    Set RGB color on the CURRENTLY SELECTED fixtures.
    
    IMPORTANT: Uses current selection! Call ma3_select() first if needed.
    
    Args:
        red, green, blue: Color values (0-100)
    
    Example workflow:
        1. ma3_select("Group ALL CAMEO")
        2. ma3_set_color(100, 0, 50)  # Magenta
    """
    return send(f"setcolor:{red} {green} {blue}") or "Failed"


@mcp.tool()
def ma3_set_position(pan: float, tilt: float) -> str:
    """
    Set pan/tilt on the CURRENTLY SELECTED fixtures.
    
    Args:
        pan, tilt: Values (0-100, 50 = center)
    """
    send(f"setattr:Pan {pan}")
    return send(f"setattr:Tilt {tilt}") or "Position set"


# =============================================================================
# Cue Management
# =============================================================================


@mcp.tool()
def ma3_store_cue(
    cue: float,
    name: str = "",
    sequence: int = 0,
    fade_in: float = 0,
    fade_out: float = 0,
    delay_in: float = 0,
    delay_out: float = 0,
    merge: bool = False,
    overwrite: bool = False,
) -> str:
    """
    Store programmer contents to a cue.
    
    💡 Best Practice: Always name cues descriptively!
    Good names: "Intro", "Verse 1", "Chorus Bump", "Blackout"

    Args:
        cue: Cue number (e.g., 1, 1.5)
        name: Cue name (recommended! e.g., "Opening Look")
        sequence: Sequence number (0 = selected sequence)
        fade_in: Fade in time in seconds
        fade_out: Fade out time in seconds (default = fade_in)
        delay_in: Delay before fade in starts (seconds)
        delay_out: Delay before fade out starts (seconds)
        merge: Merge into existing cue
        overwrite: Overwrite existing cue

    Example:
        ma3_store_cue(1, name="Opening")  # Named cue
        ma3_store_cue(2, name="Build", fade_in=3)  # With 3s fade
        ma3_store_cue(3, name="Slow Out", fade_in=1, fade_out=5)  # Split fade
    """
    # Build the store command with timing INLINE (most reliable)
    # MA3 syntax: Store Cue X "Name" CueFade "Y/Z" CueDelay "A/B" /NC
    if sequence > 0:
        store_cmd = f"Store Sequence {sequence} Cue {cue}"
    else:
        store_cmd = f"Store Cue {cue}"
    
    # Add cue name if provided
    if name:
        store_cmd += f' "{name}"'
    
    # Add timing - MA3 requires quoted values
    # Format: CueFade "InFade/OutFade" or just "InFade" if same
    if fade_in > 0 or fade_out > 0:
        if fade_out > 0 and fade_out != fade_in:
            store_cmd += f' CueFade "{fade_in}/{fade_out}"'
        elif fade_in > 0:
            store_cmd += f' CueFade "{fade_in}"'
    
    if delay_in > 0 or delay_out > 0:
        if delay_out > 0 and delay_out != delay_in:
            store_cmd += f' CueDelay "{delay_in}/{delay_out}"'
        elif delay_in > 0:
            store_cmd += f' CueDelay "{delay_in}"'
    
    # Add store options
    if merge:
        store_cmd += " /Merge"
    if overwrite:
        store_cmd += " /Overwrite"
    store_cmd += " /NC"
    
    return cmd(store_cmd) or "Cue stored"


@mcp.tool()
def ma3_store_cue_part(
    cue: float,
    part: int,
    name: str = "",
    sequence: int = 0,
    fade_in: float = 0,
    delay_in: float = 0,
) -> str:
    """
    Store programmer contents to a cue PART for complex timing.
    
    Cue Parts allow different fade times for different fixtures/attributes
    within the same cue. All parts trigger together when cue is executed.

    Args:
        cue: Cue number
        part: Part number (1-255, Part 0 is the main cue)
        name: Part name (e.g., "Colors-Slow", "Dimmer-Delayed")
        sequence: Sequence number (0 = selected sequence)
        fade_in: Fade time for this part
        delay_in: Delay before this part starts

    Example:
        # Store dimmer on Part 0 (main cue) with 1s fade
        ma3_select("1 Thru 10")
        ma3_set_attribute("Dimmer", 100)
        ma3_store_cue(1, name="Complex", fade_in=1)
        
        # Store color on Part 1 with 5s fade
        ma3_select("1 Thru 10")
        ma3_set_color(100, 0, 0)
        ma3_store_cue_part(1, part=1, name="Color-Slow", fade_in=5)
    """
    if sequence > 0:
        store_cmd = f"Store Sequence {sequence} Cue {cue} Part {part}"
    else:
        store_cmd = f"Store Cue {cue} Part {part}"
    
    if name:
        store_cmd += f' "{name}"'
    
    if fade_in > 0:
        store_cmd += f' CueFade "{fade_in}"'
    
    if delay_in > 0:
        store_cmd += f' CueDelay "{delay_in}"'
    
    store_cmd += " /NC"
    
    return cmd(store_cmd) or "Cue part stored"


@mcp.tool()
def ma3_set_cue_timing(
    cue: float,
    sequence: int = 0,
    fade_in: float = None,
    fade_out: float = None,
    delay_in: float = None,
    delay_out: float = None,
    snap_delay: float = None,
) -> str:
    """
    Set timing properties on an existing cue.

    Args:
        cue: Cue number
        sequence: Sequence number (0 = selected sequence)
        fade_in: In fade time (seconds)
        fade_out: Out fade time (seconds)
        delay_in: In delay time (seconds)
        delay_out: Out delay time (seconds)
        snap_delay: Snap delay for gobo/prism changes (seconds)

    Example:
        ma3_set_cue_timing(2, fade_in=5, fade_out=10)
        ma3_set_cue_timing(3, sequence=1, delay_in=2)
    """
    results = []
    
    if sequence > 0:
        cue_addr = f"Sequence {sequence} Cue {cue}"
    else:
        cue_addr = f"Cue {cue}"
    
    # Use Set command with Property syntax
    # MA3 syntax: Set Cue X Property "CueFade" "value"
    if fade_in is not None:
        result = cmd(f'Set {cue_addr} Property "CueInFade" "{fade_in}"')
        results.append(f"CueInFade={fade_in}: {result}")
    
    if fade_out is not None:
        result = cmd(f'Set {cue_addr} Property "CueOutFade" "{fade_out}"')
        results.append(f"CueOutFade={fade_out}: {result}")
    
    if delay_in is not None:
        result = cmd(f'Set {cue_addr} Property "CueInDelay" "{delay_in}"')
        results.append(f"CueInDelay={delay_in}: {result}")
    
    if delay_out is not None:
        result = cmd(f'Set {cue_addr} Property "CueOutDelay" "{delay_out}"')
        results.append(f"CueOutDelay={delay_out}: {result}")
    
    if snap_delay is not None:
        result = cmd(f'Set {cue_addr} Property "SnapDelay" "{snap_delay}"')
        results.append(f"SnapDelay={snap_delay}: {result}")
    
    return "; ".join(results) if results else "No timing changes specified"


@mcp.tool()
def ma3_set_cue_trigger(
    cue: float,
    trigger_type: str,
    trigger_time: float = 0,
    sequence: int = 0,
) -> str:
    """
    Set cue trigger mode for auto-follow or timed triggers.

    Args:
        cue: Cue number
        trigger_type: "Go" (manual), "Time" (auto after X sec), "Follow" (after prev done)
        trigger_time: Time in seconds (only for "Time" trigger)
        sequence: Sequence number (0 = selected sequence)

    Example:
        # Cue 2 auto-triggers 3 seconds after cue 1 starts
        ma3_set_cue_trigger(2, "Time", 3)
        
        # Cue 3 auto-triggers when cue 2 finishes (Duration complete)
        ma3_set_cue_trigger(3, "Follow")
    """
    if sequence > 0:
        cue_addr = f"Sequence {sequence} Cue {cue}"
    else:
        cue_addr = f"Cue {cue}"
    
    # Validate trigger type
    valid_types = ["Go", "Time", "Follow", "Sound", "BPM"]
    if trigger_type not in valid_types:
        return f"Invalid trigger type: {trigger_type}. Use: {', '.join(valid_types)}"
    
    # Set trigger type
    result = cmd(f'Set {cue_addr} Property "TrigType" "{trigger_type}"')
    
    # Set trigger time if using Time trigger
    if trigger_type == "Time" and trigger_time > 0:
        cmd(f'Set {cue_addr} Property "TrigTime" "{trigger_time}"')
        return f"Trigger={trigger_type}, Time={trigger_time}s: {result}"
    
    return f"Trigger={trigger_type}: {result}"


@mcp.tool()
def ma3_delete_cue(cue: float, sequence: int = 0) -> str:
    """
    Delete a cue from a sequence.

    Args:
        cue: Cue number
        sequence: Sequence number (0 = selected sequence)
    """
    if sequence > 0:
        return cmd(f"Delete Sequence {sequence} Cue {cue} /NC") or "Cue deleted"
    return cmd(f"Delete Cue {cue} /NC") or "Cue deleted"


@mcp.tool()
def ma3_goto_cue(cue: float, sequence: int = 0) -> str:
    """
    Jump to a specific cue.

    Args:
        cue: Cue number
        sequence: Sequence number (0 = selected sequence)
    """
    if sequence > 0:
        return cmd(f"Goto Cue {cue} Sequence {sequence}") or "Jumped to cue"
    return cmd(f"Goto Cue {cue}") or "Jumped to cue"


@mcp.tool()
def ma3_playback(action: str, sequence: int = 1) -> str:
    """
    Control sequence playback.

    Args:
        action: "go"/"next", "back"/"prev", "off", "top", "pause"
        sequence: Sequence number
    """
    actions = {
        "go": "Go+", "next": "Go+",
        "back": "Go-", "prev": "Go-",
        "off": "Off", "top": "Top", "pause": "Pause"
    }
    action_cmd = actions.get(action.lower())
    if not action_cmd:
        return f"Unknown action: {action}. Use: go, back, off, top, pause"
    return cmd(f"{action_cmd} Sequence {sequence}") or "Done"


@mcp.tool()
def ma3_assign_to_executor(
    object_type: str, object_number: int, page: int, executor: int, name: str = ""
) -> str:
    """
    Assign an object to an executor.

    Args:
        object_type: "Sequence", "Macro", etc.
        object_number: Object number
        page: Page number
        executor: Executor number (e.g., 201)
        name: Optional name/label for the executor button

    Example:
        ma3_assign_to_executor("Sequence", 1, 1, 201)
        ma3_assign_to_executor("Sequence", 1, 1, 201, "Main Show")
    """
    result = cmd(f"Assign {object_type} {object_number} At Page {page}.{executor}")
    if name:
        cmd(f'Label Page {page}.{executor} "{name}"')
    return result or "Assigned"


@mcp.tool()
def ma3_label_executor(page: int, executor: int, name: str) -> str:
    """
    Set or change the label/name of an executor.

    Args:
        page: Page number
        executor: Executor number (e.g., 201)
        name: The label text for the executor

    Example:
        ma3_label_executor(1, 201, "Main Show")
    """
    return cmd(f'Label Page {page}.{executor} "{name}"') or "Labeled"


@mcp.tool()
def ma3_list_executors(page: int = 1) -> str:
    """List all executors on a page with their assigned objects."""
    return send(f"listexec:{page}") or f"Could not list page {page}"


@mcp.tool()
def ma3_executor_fader(page: int, executor: int, value: float) -> str:
    """
    Set executor master fader level.
    
    Args:
        page: Page number (e.g., 1)
        executor: Executor number (e.g., 201)
        value: Fader level (0-100)
        
    Example:
        ma3_executor_fader(1, 201, 100)  # Set Page 1 Exec 201 to 100%
    """
    return send(f"execfader:{page}.{executor} {value}") or "Failed"


@mcp.tool()
def ma3_executor_go(page: int, executor: int, action: str = "go") -> str:
    """
    Control executor playback.
    
    Args:
        page: Page number
        executor: Executor number
        action: "go", "off", "top", "pause", "toggle", "on", "flash"
        
    Example:
        ma3_executor_go(1, 201, "go")    # Trigger Go on executor
        ma3_executor_go(1, 201, "off")   # Turn off executor
    """
    return send(f"execgo:{page}.{executor} {action}") or "Failed"


@mcp.tool()
def ma3_get_current_cue(sequence: int = 0) -> str:
    """
    Get current cue position of a sequence.

    Args:
        sequence: Sequence number (0 = selected sequence)
    """
    return send(f"getcue:{sequence}") or "Could not get cue"


@mcp.tool()
def ma3_get_sequence_status(sequence: int = 1) -> str:
    """Get detailed status of a sequence including playback state."""
    return send(f"seqstatus:{sequence}") or f"Could not get sequence {sequence}"

# =============================================================================
# Object Queries
# =============================================================================


@mcp.tool()
def ma3_query(address: str) -> str:
    """
    Query an MA3 object by address.

    Args:
        address: Object address (e.g., "Sequence 1", "Page 1.201")

    Returns:
        Object info with name, class, children
    """
    return send(f"?{address}") or f"Object not found: {address}"


@mcp.tool()
def ma3_get_property(address: str, property_name: str) -> str:
    """
    Get a property value from an MA3 object.
    
    NOTE: For cue timing properties, use address format "Sequence X Cue Y"
    and property names like "CueInFade", "CueOutFade", "CueInDelay", "TrigType", etc.

    Args:
        address: Object address (e.g., "Sequence 1 Cue 2", "Group 1")
        property_name: Property name (e.g., "name", "CueInFade", "TrigType")
        
    Example:
        ma3_get_property("Sequence 1 Cue 2", "CueInFade")
        ma3_get_property("Sequence 1 Cue 2", "TrigType")
    """
    # Try direct get first (works for simple properties)
    result = send(f"get:{address}.{property_name}")
    if result and result != "null" and not result.startswith("ERR"):
        return result
    
    # For nil results, try the alternative format for nested objects like cues
    # Use Property keyword format which is more reliable for cue properties
    result = send(f"get:{address} {property_name}")
    return result or f"Property not found: {property_name}"


@mcp.tool()
def ma3_get_all_properties(address: str) -> str:
    """
    Get ALL properties of an MA3 object as JSON.
    
    Useful for discovering available properties on cues, sequences, etc.

    Args:
        address: Object address (e.g., "Sequence 1 Cue 2")
        
    Returns:
        JSON with all property names and values
        
    Example:
        ma3_get_all_properties("Sequence 1 Cue 2")  # See all cue properties
    """
    return send(f"props:{address}") or f"Could not get properties for {address}"


@mcp.tool()
def ma3_list_children(address: str) -> str:
    """List children of an MA3 object."""
    return send(f"children:{address}") or f"No children for {address}"


# =============================================================================
# Inspection & Verification Tools
# =============================================================================


@mcp.tool()
def ma3_list_programmer_detailed() -> str:
    """
    Get DETAILED programmer contents with all attribute values.
    
    Unlike ma3_list_programmer(), this shows the actual values for each
    attribute, not just which fixtures have values in the programmer.
    
    Returns:
        JSON with fixtures and their attribute values:
        {
            "fixtures": [
                {"name": "MAC Aura 1", "fid": 1, "attributes": {"Dimmer": 100, "Pan": 50}}
            ],
            "total_fixtures": 5,
            "total_attributes": 15
        }
    
    Use this to verify what's in the programmer BEFORE calling ma3_store_cue().
    """
    return send("progdetail:") or "Programmer is empty"


@mcp.tool()
def ma3_get_cue_contents(
    cue: float,
    sequence: int = 1,
    part: int = None
) -> str:
    """
    Get information about a stored cue.
    
    Shows cue name, timing, trigger type, and part information.
    
    Args:
        cue: Cue number
        sequence: Sequence number (default 1)
        part: Specific part number (optional)
    
    Returns:
        JSON with cue info:
        {
            "cue": 1,
            "name": "Opening Look",
            "fade_in": "3",
            "fade_out": "5",
            "trigger_type": "Go",
            "has_parts": true,
            "part_count": 3
        }
    
    NOTE: For detailed fixture values, use the Track Sheet in MA3.
    """
    query = str(cue)
    query += f" {sequence}"
    if part is not None:
        query += f" {part}"
    return send(f"cuecontents:{query}") or f"Cue {cue} not found"


@mcp.tool()
def ma3_get_fixture_status(fixture_id: int) -> str:
    """
    Get current status for a specific fixture.
    
    Shows parameter values from programmer and current output.
    
    Args:
        fixture_id: Fixture ID number
    
    Returns:
        JSON with fixture status:
        {
            "fixture_id": 1,
            "name": "MAC Aura 1",
            "patch": "1.001",
            "selected": true,
            "in_programmer": true,
            "programmer_values": {"Dimmer": 100, "Pan": 50},
            "output_values": {"Dimmer": 100, "Pan": 50}
        }
    
    Use this to verify what values a fixture has in programmer and output.
    """
    return send(f"fixstatus:{fixture_id}") or f"Fixture {fixture_id} not found"


@mcp.tool()
def ma3_get_sequence_overview(sequence: int = 1) -> str:
    """
    Get an overview of all cues in a sequence.
    
    Shows all cues with their names, timing, and trigger info.
    
    Args:
        sequence: Sequence number (default 1)
    
    Returns:
        JSON with sequence overview:
        {
            "sequence": 1,
            "name": "Main",
            "is_playing": false,
            "cue_count": 10,
            "cues": [
                {"cue": 1, "name": "Intro", "fade_in": "3", "trigger": "Go"},
                {"cue": 2, "name": "Verse", "fade_in": "2", "trigger": "Follow"}
            ]
        }
    """
    return send(f"seqoverview:{sequence}") or f"Sequence {sequence} not found"


# =============================================================================
# Entry Point
# =============================================================================


def main():
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()