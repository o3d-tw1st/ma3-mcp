# grandMA3 Lua Plugin API Reference

> **Version**: grandMA3 2.0  
> **Lua Version**: 5.4.4  
> **Source**: https://help.malighting.com/grandMA3/2.0/HTML/plugins.html

## Project Structure

```
ma3_mcp/
├── server.py      # MCP tools (@mcp.tool() definitions)
├── ma3_comm.py    # File-based IPC (send/cmd functions)
└── __init__.py

plugin.lua         # grandMA3 Lua plugin (command dispatcher)
```

Communication uses file IPC:
- Commands: `/Users/Shared/MA3/mcp_command.txt`
- Responses: `/Users/Shared/MA3/mcp_response.txt`

---

## Table of Contents

1. [Core Concepts](#core-concepts)
2. [Handle (light_userdata)](#handle-light_userdata)
3. [Object-Free API Functions](#object-free-api-functions)
4. [Object API Functions](#object-api-functions)
5. [Fixture & Channel Functions](#fixture--channel-functions)
6. [DMX Functions](#dmx-functions)
7. [Programmer Functions](#programmer-functions)
8. [Command Execution](#command-execution)
9. [Variables](#variables)
10. [Common Patterns](#common-patterns)
11. [Important Notes for MCP Plugin](#important-notes-for-mcp-plugin)
12. [Quick Reference: Object Address Formats](#quick-reference-object-address-formats)
13. [Cue Storage, Timing, and Triggers](#cue-storage-timing-and-triggers)

---

## Core Concepts

### Plugin Structure
- Plugins are stored in the **Plugins Pool**
- Each plugin can contain multiple **Lua components**
- Components are `.lua` files stored in `gma3_library/datapools/plugins/`
- Use `ReloadAllPlugins` keyword to reload after external edits

### Two API Categories
1. **Object-Free API**: Standalone functions (e.g., `Printf()`, `Cmd()`)
2. **Object API**: Methods on handle objects (e.g., `obj:Dump()`, `obj:Children()`)

---

## Handle (light_userdata)

A **handle** is a unique identifier referencing a grandMA3 object (sequence, cue, preset, fixture, etc.).

### Properties of Handle Objects
- `name` - Object name
- `class` - Object class
- `no` - Object number
- `patch` - Patch address (for fixtures)

### Handle Conversion Functions

| Function | Description |
|----------|-------------|
| `FromAddr(string[, handle])` | Convert address string to handle |
| `ToAddr(handle)` | Convert handle to address string |
| `HandleToStr(handle)` | Convert handle to hex string |
| `HandleToInt(handle)` | Convert handle to integer |
| `StrToHandle(string)` | Convert hex string to handle |
| `IntToHandle(integer)` | Convert integer to handle |

### Example
```lua
local seqHandle = FromAddr("13.13.1.5.1")  -- Numbered address
local seqHandle2 = FromAddr("Sequences.Default", DataPool())  -- Named address
Printf("Address: " .. seqHandle:Addr())
Printf("Native: " .. seqHandle:AddrNative())
```

---

## Object-Free API Functions

### Output Functions

| Function | Description |
|----------|-------------|
| `Printf(string)` | Print to Command Line History (supports format strings) |
| `Echo(string)` | Print to Command Line (different display) |
| `ErrPrintf(string)` | Print error message |

**⚠️ NOTE**: In background/timer plugins, use `Printf()` - `Echo()` may not work in all contexts.

### Object Access Functions

| Function | Description | Return |
|----------|-------------|--------|
| `Root()` | Get root object | Handle |
| `DataPool()` | Get current data pool | Handle |
| `Programmer()` | Get programmer object | Handle |
| `Patch()` | Get patch object | Handle |
| `Pult()` | Get console object | Handle |
| `ShowData()` | Get show data object | Handle |
| `Selection()` | Get current selection object | Handle |
| `CurrentUser()` | Get current user | Handle |
| `CurrentProfile()` | Get current profile | Handle |
| `CurrentExecPage()` | Get current executor page | Handle |
| `SelectedSequence()` | Get selected sequence | Handle |
| `MasterPool()` | Get master pool | Handle |

**⚠️ WARNING**: `Root()` causes "UI functionality out of non-UI thread" error in Timer/background plugins!

### Object Query

| Function | Description |
|----------|-------------|
| `ObjectList(string)` | Get table of handles from selection string |
| `IsObjectValid(handle)` | Check if handle is still valid |

```lua
-- Get fixtures 1-10
local fixtures = ObjectList("Fixture 1 Thru 10")
for i, fix in ipairs(fixtures) do
    Printf("Fixture: %s - Patch: %s", fix.name, fix.patch)
end
```

---

## Object API Functions

Methods called on handle objects using colon notation: `object:Method()`

| Function | Description |
|----------|-------------|
| `Addr([handle, boolean])` | Get numbered address string |
| `AddrNative([handle, boolean])` | Get named address string |
| `Children()` | Get table of child handles |
| `Count()` | Get number of children |
| `Ptr(index)` | Get child at index (1-based) |
| `Dump()` | Print all object info to Command Line History |
| `Get(property)` | Get property value |
| `GetClass()` | Get object class name |
| `HasActivePlayback()` | Check if object has active playback |
| `Export(path, name)` | Export object |
| `Import(path, name)` | Import into object |

### Accessing Children
```lua
local dataPool = DataPool()
local sequences = dataPool.Sequences      -- Access by property name
local seq1 = dataPool.Sequences[1]         -- Access by index

-- Or iterate
local children = seq1:Children()
for i, child in ipairs(children) do
    Printf("Child %d: %s", i, child.name)
end
```

---

## Fixture & Channel Functions

### Fixture Selection

| Function | Description | Return |
|----------|-------------|--------|
| `SelectionFirst()` | Get first selected fixture index | Integer (0-based patch index) |
| `SelectionNext(index)` | Get next selected fixture | Integer |
| `SelectionCount()` | Get count of selected fixtures | Integer |
| `GetSubfixture(index)` | Get fixture handle by patch index | Handle |
| `GetSubfixtureCount()` | Get total patched fixture count | Integer |

```lua
-- Iterate through selection
local idx = SelectionFirst()
while idx do
    local fixture = GetSubfixture(idx)
    Printf("Fixture: %s", fixture.name)
    idx = SelectionNext(idx)
end
```

### UI Channels (User Interface Channels)

UI Channels represent the parameter controls visible in the encoder bar.

| Function | Description | Return |
|----------|-------------|--------|
| `GetUIChannelCount()` | Total UI channels in show | Integer |
| `GetUIChannels(fixture_idx/handle[, bool])` | Get UI channels for fixture | Table of indexes or handles |
| `GetUIChannelIndex(fixture_idx, attr_idx)` | Get UI channel for fixture+attribute | Integer |
| `GetAttributeByUIChannel(ui_ch_idx)` | Get attribute handle from UI channel | Handle |
| `GetAttributeIndex(string)` | Get attribute index by name | Integer (0-based) |
| `GetAttributeCount()` | Get total attribute count | Integer |

```lua
-- Get UI channel for fixture 1's Dimmer
local fixtureIdx = SelectionFirst()
local attrIdx = GetAttributeIndex("Dimmer")
local uiChIdx = GetUIChannelIndex(fixtureIdx, attrIdx)

-- Get all UI channels for a fixture (with handles)
local uiChannels = GetUIChannels(fixtureIdx, true)
for _, ch in ipairs(uiChannels) do
    Printf("UIChannel Index: %d, SubAttribute: %s", ch.INDEX-1, ch.SUBATTRIBUTE)
end
```

### RT Channels (Real-Time Channels)

RT Channels represent the actual DMX output channels.

| Function | Description | Return |
|----------|-------------|--------|
| `GetRTChannelCount()` | Total RT channels | Integer |
| `GetRTChannels(fixture_idx/handle[, bool])` | Get RT channels for fixture | Table |
| `GetRTChannel(rt_ch_idx)` | Get RT channel info | Table |

**RT Channel Table Properties**:
- `subfixture` - Handle to subfixture
- `fixture` - Handle to fixture  
- `dmx_channel` - Handle to DMX channel
- `dmx_default` - Default DMX value
- `dmx_highlight` - Highlight DMX value
- `dmx_lowlight` - Lowlight DMX value
- `ui_index_first` - First UI channel index
- `rt_index` - RT channel index
- `freq` - Update frequency
- `info` - Additional info table
- `patch` - Patch info table

```lua
-- Get RT channel info for first fixture
local rtChannels = GetRTChannels(SelectionFirst())
local rtInfo = GetRTChannel(rtChannels[1])
Printf("DMX Default: %d", rtInfo.dmx_default)
Printf("DMX Highlight: %d", rtInfo.dmx_highlight)
```

---

## DMX Functions

| Function | Description | Return |
|----------|-------------|--------|
| `GetDMXValue(addr[, universe, percent])` | Get single DMX value | Integer |
| `GetDMXUniverse(universe[, percent])` | Get all 512 values for universe | Table |

### Parameters
- `addr` - DMX address (1-512)
- `universe` - Universe number (1-1024)
- `percent` - `true` for 0-100%, `false` for 0-255

```lua
-- Get DMX address 1 in universe 4 as raw DMX value
local value = GetDMXValue(1, 4, false)
Printf("DMX 4.001 = %d", value)

-- Get entire universe as percentages
local dmxTable = GetDMXUniverse(1, true)
for addr, val in ipairs(dmxTable) do
    if val > 0 then
        Printf("Addr %d: %d%%", addr, val)
    end
end
```

---

## Programmer Functions

| Function | Description |
|----------|-------------|
| `Programmer()` | Get programmer handle |
| `GetPresetData(handle[, phaser_only, by_fixtures])` | Get preset data table |

```lua
local prog = Programmer()
prog:Dump()  -- See all programmer info

-- Get preset data
local preset = DataPool().PresetPools[1][1]  -- Dimmer preset 1
local data = GetPresetData(preset, false, true)
-- data.by_fixtures contains data keyed by fixture ID
```

---

## Command Execution

| Function | Description | Return |
|----------|-------------|--------|
| `Cmd(string[, undo_handle])` | Execute command synchronously | "OK", "Syntax Error", "Illegal Command" |
| `CmdIndirect(string[, handle, handle])` | Execute asynchronously | - |
| `CmdIndirectWait(string[, handle, handle])` | Execute async and wait | - |

**⚠️ WARNING**: `Cmd()` blocks the Lua task. Bad commands can freeze the system!

```lua
Cmd("ClearAll")
local result = Cmd("Fixture 1 At 50")
Printf("Result: %s", result)  -- "OK"
```

---

## Variables

### Variable Sets
- `UserVars()` - User-specific variables
- `GlobalVars()` - Global session variables

### Functions

| Function | Description |
|----------|-------------|
| `GetVar(handle, name)` | Get variable value |
| `SetVar(handle, name, value)` | Set variable value |
| `DelVar(handle, name)` | Delete variable |

```lua
SetVar(GlobalVars(), "myVar", 42)
local val = GetVar(GlobalVars(), "myVar")
Printf("Value: %s", tostring(val))
```

---

## Common Patterns

### Safe Object Access with pcall
```lua
local success, result = pcall(function()
    return obj:SomeMethod()
end)
if success then
    -- Use result
else
    Printf("Error: %s", tostring(result))
end
```

### Get Object by Address (Alternative to Root())
```lua
-- Don't use Root() in timer plugins!
-- Use ObjectList or FromAddr instead
local fixtures = ObjectList("Fixture 1")
if fixtures and #fixtures > 0 then
    local fix = fixtures[1]
end
```

### Iterate Fixtures in Selection
```lua
local function processSelection()
    local idx = SelectionFirst()
    if not idx then
        ErrPrintf("No fixtures selected")
        return
    end
    
    while idx do
        local fixture = GetSubfixture(idx)
        Printf("Processing: %s", fixture.name)
        idx = SelectionNext(idx)
    end
end
```

### Get Fixture Attribute Value via DMX
```lua
local function getFixtureDimmer(fixtureIdx)
    local rtChannels = GetRTChannels(fixtureIdx)
    if not rtChannels or #rtChannels == 0 then
        return nil
    end
    
    local rtInfo = GetRTChannel(rtChannels[1])
    if rtInfo and rtInfo.dmx_channel then
        -- Get the DMX address from the channel
        -- Note: Need to extract universe/address from dmx_channel handle
    end
end
```

---

## Important Notes for MCP Plugin

### Thread Restrictions
When running in a Timer or background context (like our MCP polling plugin):

1. **❌ DON'T USE**:
   - `Root()` - Causes "UI functionality out of non-UI thread" error
   - `load()` - Dynamic code execution not allowed
   - Direct UI manipulation functions

2. **✅ SAFE TO USE**:
   - `Printf()` - For logging
   - `Cmd()` - For executing commands
   - `GetDMXValue()`, `GetDMXUniverse()` - For reading DMX output
   - `GetSubfixture()`, `GetRTChannels()`, `GetRTChannel()` - For fixture info
   - `ObjectList()` - For getting object handles
   - `FromAddr()` - For converting addresses to handles
   - `DataPool()`, `Programmer()` - For accessing pools
   - File I/O via standard Lua `io` library

### Getting Fixture Values - Best Approaches

**Option 1: Via DMX Universe** (most reliable)
```lua
local dmxTable = GetDMXUniverse(1, true)  -- Universe 1, percent mode
-- Access by DMX address
```

**Option 2: Via RT Channel**
```lua
local fixtureIdx = 0  -- 0-based patch index
local rtChannels = GetRTChannels(fixtureIdx)
local rtInfo = GetRTChannel(rtChannels[1])
-- rtInfo contains dmx_default, dmx_highlight, etc.
```

**Option 3: Via ObjectList**
```lua
local fixtures = ObjectList("Fixture 1")
if fixtures then
    local fix = fixtures[1]
    Printf("Name: %s, Patch: %s", fix.name, fix.patch)
end
```

### Fixture Index Notes
- `SelectionFirst()` returns **0-based** patch index
- `GetSubfixture(index)` takes **0-based** patch index
- Fixture IDs (FID/CID) are different from patch indexes!
- Use `ObjectList("Fixture 1")` if you want to query by fixture ID

### Error Handling Pattern for MCP
```lua
local function safePoll()
    local success, err = pcall(function()
        -- Your polling code here
    end)
    if not success then
        Printf("MCP Poll Error: %s", tostring(err))
    end
end
```

---

## Quick Reference: Object Address Formats

| Object | Address Format |
|--------|----------------|
| Fixture by ID | `"Fixture 1"` or `"Fixture 1 Thru 10"` |
| Sequence | `"Sequence 1"` or `DataPool().Sequences[1]` |
| Page | `"Page 1"` |
| Executor | `"Page 1.201"` (page.executor) |
| Cue | `"Sequence 1.Cue 1"` |
| Preset | `"Preset 1.1"` or `DataPool().PresetPools[1][1]` |
| Group | `"Group 1"` |
| Programmer | `Programmer()` (function, not string) |

---

## Cue Storage, Timing, and Triggers

### 💡 Best Practice: Always Name Cues Descriptively!
Cue names should describe the scene, not just be numbers. Good examples:
- `"Intro"`, `"Verse 1"`, `"Chorus Bump"`, `"Blackout"`, `"Act2-Scene3"`

### Store Cue Syntax
```lua
-- Basic cue storage
Cmd('Store Cue 1 /NC')  -- /NC = No Confirmation

-- With name (ALWAYS recommended!)
Cmd('Store Cue 1 "Opening Look" /NC')

-- With fade and delay (times must be quoted!)
Cmd('Store Cue 2 "Slow Build" CueFade "5" CueDelay "2" /NC')

-- With split In/Out fade (3s fade in, 7s fade out)
Cmd('Store Cue 3 "Dramatic Exit" CueFade "3/7" /NC')

-- With delay split (InDelay/OutDelay)
Cmd('Store Cue 4 CueFade "2" CueDelay "1/3" /NC')
```

### Cue Timing Keywords
| Keyword | Description | Example |
|---------|-------------|---------|
| `CueFade` | In fade time (or In/Out with slash) | `CueFade "3"` or `CueFade "2/5"` |
| `CueDelay` | In delay time (or In/Out with slash) | `CueDelay "1"` or `CueDelay "0/2"` |
| `CueInFade` | Fade time for values going UP | `CueInFade "3"` |
| `CueOutFade` | Fade time for dimmer going DOWN | `CueOutFade "7"` |
| `CueInDelay` | Delay before In fade starts | `CueInDelay "2"` |
| `CueOutDelay` | Delay before Out fade starts | `CueOutDelay "1"` |
| `SnapDelay` | Delay for snap attributes (gobos, etc.) | `SnapDelay "0.5"` |

### Cue Trigger Types
Cues can be triggered automatically after the previous cue:

| Trigger Type | Description |
|--------------|-------------|
| `Go` | Manual trigger (default) - requires Go command |
| `Time` | Auto-trigger X seconds after previous cue STARTS |
| `Follow` | Auto-trigger when previous cue FINISHES (Duration complete) |
| `Sound` | Trigger on sound input (frequency bands) |
| `BPM` | Trigger on beat detection |

```lua
-- Set trigger type using Set command
Cmd('Set Cue 2 Property "TrigType" "Time"')
Cmd('Set Cue 2 Property "TrigTime" "3"')  -- 3 seconds after cue 1 starts

Cmd('Set Cue 3 Property "TrigType" "Follow"')  -- After cue 2 finishes
```

### Cue Parts (Complex Timing)
Cue Parts allow different fade times for different fixtures/attributes within the same cue.

**Use Cases:**
- Different fade times for different fixture groups
- Delayed color change while dimmer stays constant
- Complex scene builds with staggered timing

```lua
-- Store main cue (Part 0 - automatic)
Cmd('Select Fixture 1 Thru 10')
Cmd('Attribute "Dimmer" At 100')
Cmd('Store Cue 5 "Complex Scene" CueFade "2" /NC')

-- Store Part 1 with different timing
Cmd('Select Fixture 11 Thru 20')
Cmd('Attribute "ColorRGB_R" At 100')
Cmd('Store Cue 5 Part 1 "Colors-Slow" CueFade "8" /NC')

-- Store Part 2 with delay
Cmd('Select Fixture 21 Thru 30')
Cmd('Attribute "Dimmer" At 50')
Cmd('Store Cue 5 Part 2 "Delayed-Dim" CueFade "3" CueDelay "5" /NC')
```

**Part Execution:**
- All parts trigger together when the cue is triggered
- Each part uses its own fade and delay times
- Part 0 is the default; higher part numbers are optional
- Parts can have names for identification

### Cue Transitions
The `Transition` property controls the acceleration curve of the fade:
- `Linear` (default) - constant speed
- `Slow` / `Slow+` - slow start, fast end
- `Fast` / `Fast+` - fast start, slow end
- `SCurve` - slow start and end
- `Swing-` / `Swing` / `Swing+` - various S-curve variations

```lua
Cmd('Set Cue 5 Property "Transition" "SCurve"')
```

---

## File I/O (Standard Lua)

```lua
-- Read file
local f = io.open("/path/to/file", "r")
if f then
    local content = f:read("*all")
    f:close()
end

-- Write file
local f = io.open("/path/to/file", "w")
if f then
    f:write("content")
    f:close()
end
```

---

## Links

- [Full Plugin Documentation](https://help.malighting.com/grandMA3/2.0/HTML/plugins.html)
- [Object-Free API](https://help.malighting.com/grandMA3/2.0/HTML/lua_objectfree.html)
- [Object API](https://help.malighting.com/grandMA3/2.0/HTML/lua_object.html)
- [Handle Reference](https://help.malighting.com/grandMA3/2.0/HTML/lua_handle.html)
- [Variable Functions](https://help.malighting.com/grandMA3/2.0/HTML/lua_variables.html)

==========================================
Object-Free API
==========================================

Echo(string:formatted_command ...): nothing
ErrEcho(string:formatted_command ...): nothing
Printf(string:formatted_command ...): nothing
ErrPrintf(string:formatted_command ...): nothing
Cmd(string:formatted_command[ ,light_userdata:undo], ...): string:command_execution_result ('Ok', 'Syntax Error', 'Illegal Command', ...)
CmdIndirect(string:command[, light_userdata:undo[, light_userdata:target]]): nothing
CmdIndirectWait(string:command[, light_userdata:undo[, light_userdata:target]]): nothing
CallRealtimeLockedProtected(function:name): result of function
HostOS(nothing): string:ostype
HostType(nothing): string:hosttype
HostSubType(nothing): string:hostsubtype
HostRevision(nothing): string:hostrevision
SerialNumber(nothing): string:serialnumber
OverallDeviceCertificate(nothing): light_userdata:handle
RemoteCommand(string:ip, string:command): boolean:success
OpenMessageQueue(string:queue name): boolean:success
CloseMessageQueue(string:queue name): boolean:success
SendLuaMessage(string:ip/station, string:channel name, table:data): boolean:success
ReleaseType(nothing): string:releasetype
DevMode3d(nothing): string:devmode3d
Version(nothing): string:version
BuildDetails(nothing): table:build_details
GetShowFileStatus(nothing): string:showfile_status
ConfigTable(nothing): table:config_details
CmdObj(nothing): light_userdata:handle
Root(nothing): light_userdata:handle
Pult(nothing): light_userdata:handle
DefaultDisplayPositions(nothing): light_userdata:handle
Patch(nothing): light_userdata:handle
FixtureType(nothing): light_userdata:handle
ShowData(nothing): light_userdata:handle
ShowSettings(nothing): light_userdata:handle
DataPool(nothing): light_userdata:handle
MasterPool(nothing): light_userdata:handle
DeviceConfiguration(nothing): light_userdata:handle
Programmer(nothing): light_userdata:handle
ProgrammerPart(nothing): light_userdata:handle
Selection(nothing): light_userdata:handle
CurrentUser(nothing): light_userdata:handle
CurrentProfile(nothing): light_userdata:handle
CurrentEnvironment(nothing): light_userdata:handle
CurrentScreenConfig(nothing): light_userdata:handle
CurrentExecPage(nothing): light_userdata:handle
SelectedSequence(nothing): light_userdata:handle
GetCurrentCue(nothing): light_userdata:handle
SelectedTimecode(nothing): light_userdata:handle
SelectedLayout(nothing): light_userdata:handle
SelectedTimer(nothing): light_userdata:handle
GetSelectedAttribute(nothing): light_userdata:handle
SelectedFeature(nothing): light_userdata:handle
SelectedDrive(nothing): light_userdata:handle
GetExecutor(integer:executor): light_userdata:executor, light_userdata:page
LoadExecConfig(light_userdata:executor): nothing
SaveExecConfig(light_userdata:executor): nothing
SelectionTable(nothing): table of subfixture_index
ChannelTable(string:attribute_name or integer:attribute_index): table of ui_channel_index
SelectionFirst(nothing): integer:first_subfixture_index, integer:x, integer:y, integer:z
SelectionNext(integer:current_subfixture_index): integer:next_subfixture_index, integer:x, integer:y, integer:z
SelectionCount(nothing): integer:amount_of_selected_subfixtures
SelectionComponentX(nothing): integer:min, integer:max, integer:index, integer:block, integer:group
SelectionComponentY(nothing): integer:min, integer:max, integer:index, integer:block, integer:group
SelectionComponentZ(nothing): integer:min, integer:max, integer:index, integer:block, integer:group
GetSubfixtureCount(nothing): integer:subfixture_count
GetSubfixture(integer:subfixture_index): light_userdata:subfixture
GetUIChannelCount(nothing): integer:ui_channel_count
GetRTChannelCount(nothing): integer:rt_channel_count
GetAttributeCount(nothing): integer:attribute_count
GetUIChannels(integer:subfixture_index or light_userdata: subfixture_handle[, boolean:return_as_handles]): {integer:ui_channels} or {light_userdata:ui_channels}
GetRTChannels(integer:fixture index or light_userdata: reference_to_fixture_object[, boolean:return_as_handles]): {integer:rt_channels} or {light_userdata:rt_channels}
GetUIChannel(integer:ui_channel_index or light_userdata: subfixture_reference, integer:attribute_index or string:attribute_name): table:ui_channel_descriptor
GetRTChannel(integer:rt_channel_index): table:rt_channel_descriptor
GetAttributeByUIChannel(integer:ui channel index): light_userdata:reference_to_attribute
FirstDmxModeFixture(light_userdata:dmxmode): light_userdata:fixture
NextDmxModeFixture(light_userdata:fixture): light_userdata:fixture
GetAttributeIndex(string:attribute_name): integer:attribute_index
GetUIChannelIndex(integer:subfixture_index, integer:attribute_index): integer:ui_channel_index
GetChannelFunctionIndex(integer:ui_channel_index, integer:attribute_index): integer:channel_function_index
GetChannelFunction(integer:ui_channel_index, integer:attribute_index): light_userdata:handle
GetTokenName(string:short_name): string:full_name
GetTokenNameByIndex(integer:token_index): string:full_name
SetProgPhaser(integer:ui_channel_index, {['abs_preset'=light_userdata:handle], ['rel_preset'=light_userdata:handle], ['fade'=number:seconds], ['delay'=number:seconds], ['speed'=number:hz], ['phase'=number:degree], ['measure'=number:percent], ['gridpos'=integer:value], {['channel_function'=integer:value], ['absolute'=number:percent], ['absolute_value'=integer:value], ['relative'=number:percent], ['accel'=number:percent[, 'accel_type'=integer:enum_value(Enums.SplineType)]], ['decel'=number:percent[, 'decel_type'=integer:enum_value(Enums.SplineType)]], ['trans'=number:percent], ['width'=number:percent], ['integrated'=light_userdata:preset_handle]}}): nothing
SetProgPhaserValue(integer:ui_channel_index, integer:step, {['channel_function'=integer:value], ['absolute'=number:percent], ['absolute_value'=integer:value], ['relative'=number:percent], ['accel'=number:percent[, 'accel_type'=integer:enum_value(Enums.SplineType)]], ['decel'=number:percent[, 'decel_type'=integer:enum_value(Enums.SplineType)]], ['trans'=number:percent], ['width'=number:percent], ['integrated'=light_userdata:preset_handle]}): nothing
GetProgPhaser(integer:ui_channel_index, boolean:phaser_only): {['abs_preset'=light_userdata:handle], ['rel_preset'=light_userdata:handle], ['fade'=float:seconds], ['delay'=float:seconds], ['speed'=float:hz], ['phase'=float:degree], ['measure'=float:percent], ['gridpos'=integer:value], ['mask_active_phaser'=integer:bitmask], ['mask_active_value'=integer:bitmask], ['mask_individual'=integer:bitmask], {['channel_function'=integer:value], ['absolute'=float:percent], ['absolute_value'=integer:value], ['relative'=float:percent], ['accel'=float:percent[, 'accel_type'=integer:enum_value(Enums.SplineType)]], ['decel'=float:percent[, 'decel_type'=integer:enum_value(Enums.SplineType)]], ['trans'=float:percent], ['width'=float:percent], ['integrated'=light_userdata:preset_handle]}}
GetProgPhaserValue(integer:ui_channel_index, integer:step): {['channel_function'=integer:value], ['absolute'=number:percent], ['absolute_value'=number:value], ['relative'=number:percent], ['accel'=number:percent[, 'accel_type'=integer:enum_value(Enums.SplineType)]], ['decel'=number:percent[, 'decel_type'=integer:enum_value(Enums.SplineType)]], ['trans'=number:percent], ['width'=number:percent], ['integrated'=light_userdata:preset_handle]}
SetColor(string:color_model('RGB', 'xyY', 'Lab', 'XYZ', 'HSB'), float:tripel1, float:tripel2, float:tripel3, float:brightness, float:quality, boolean:const_brightness): integer:flag
GetPresetData(light_userdata:preset_handle[, boolean:phasers_only(default=false)[, boolean:by_fixtures(default=true)]]): table:phaser_data
ColMeasureDeviceDarkCalibrate(nothing): integer:flag
ColMeasureDeviceDoMeasurement(nothing): table:values
GetObject(string:address): light_userdata:handle
ObjectList(string:address[, {['selected_as_default'=boolean:enabled], ['reverse_order'=boolean:enabled]}): {light_userdata:handles}
FromAddr(string:address[, light_userdata:base_handle]): light_userdata:handle
ToAddr(light_userdata:handle, boolean:with_name[, boolean:use_visible_addr]): string:address
IntToHandle(integer:handle): light_userdata:handle
HandleToInt(light_userdata:handle): integer:handle
StrToHandle(string:handle(in H#... format)): light_userdata:handle
HandleToStr(light_userdata:handle): string:handle(in H#... format)
IsObjectValid(light_userdata:handle): boolean:valid
Export(string:file_name, table:export_data): boolean:success
Import(string:file_name): table:content
ExportJson(string:file_name, table:export_data): boolean:success
ExportCSV(string:file_name, table:export_data): boolean:success
HookObjectChange(function:callback, light_userdata:handle, light_userdata:plugin_handle[, light_userdata:target]): integer:hook_id
PrepareWaitObjectChange(light_userdata:handle[ ,integer:change_level_threshold]): boolean:true or nothing
Unhook(integer:hook_id): nothing
UnhookMultiple(function:callback(can be nil), light_userdata:handle to target(can be nil), light_userdata:handle to context (can be nil)): integer:amount of removed hooks
DumpAllHooks(nothing): nothing
GetPath(string:path_type or integer:path_type(Enums.PathType)[ ,boolean:create]): string:path
GetPathType(light_userdata:target_object[ ,integer:content_type (Enums.PathContentType)]): string:path_type_name
GetPathOverrideFor(string:path_type or integer:path_type(Enums.PathType), string:path[ ,boolean:create]): string:overwritten_path
GetPathSeparator(nothing): string:seperator
FileExists(string:path): boolean:result
CopyFile(string:source_path, string:destination_path): boolean:result
CreateDirectoryRecursive(string:path): boolean:result
SyncFS(nothing): nothing
DirList(string:path[ ,string:filter]): table of {name:string, size:int, time:int}
StartProgress(string:name): integer:progressbar_index
StopProgress(integer:progressbar_index): nothing
SetProgressText(integer:progressbar_index, string:text): nothing
SetProgressRange(integer:progressbar_index, integer:start, integer:end): nothing
SetProgress(integer:progressbar_index, integer:value): nothing
IncProgress(integer:progressbar_index[, integer:delta]): nothing
GetPropertyColumnId(light_userdata:handle, string:property_name): integer:column_id
GetAttributeColumnId(light_userdata:handle, light_userdata:attribute): integer:column_id
Keyboard(integer:display_index, string:type('press', 'char', 'release')[ ,string:char(for type 'char') or string:keycode, boolean:shift, boolean:ctrl, boolean:alt, boolean:numlock]): nothing
Mouse(integer:display_index, string:type('press', 'move', 'release')[ ,string:button('Left', 'Middle', 'Right' for 'press', 'release') or integer:abs_x, integer:abs_y)]): nothing
Touch(integer:display_index, string:type('press', 'move', 'release'), integer:touch_id, integer:abs_x, integer:abs_y): nothing
Time(nothing): integer:time
MouseObj(nothing): light_userdata:handle
TouchObj(nothing): light_userdata:handle
KeyboardObj(nothing): light_userdata:handle
Timer(function:timer_function, integer:delay_time, integer:max_count[, function:cleanup][, light_userdata:context object]): nothing
FindBestDMXPatchAddr(light_userdata:patch, integer:starting_address, integer:footprint): integer:absolute_address
CheckDMXCollision(light_userdata:dmx_mode, string:dmx_address[ ,integer:count[ ,integer:break_index]]): boolean:no_collision_found
CheckFIDCollision(integer:fid[, integer:count[, integer:type]]): boolean:no_collision_found
GetDMXValue(integer:address[ ,integer:universe, boolean:mode_percent]): integer:dmx_value
GetDMXUniverse(integer:universe[ ,boolean:modePercent]): {integer:dmx_values}
SetLED(light_userdata:usb_device_object_handle, table:led_values): nothing
GetButton(light_userdata:usb_device_object_handle): table of boolean:state
CreateUndo(string:undo_text): light_userdata:undo_handle
CloseUndo(light_userdata:undo_handle): boolean:closed (true if was closed, false - if it's still in use)
DeskLocked(nothing): boolean:desk_is_locked
RemoteCallRunning(nothing): boolean:remotecall_is_running
NeedShowSave(nothing): boolean:need_show_save
RefreshLibrary(light_userdata:handle): nothing
SelectionNotifyBegin(light_userdata:associated_context): nothing
SelectionNotifyObject(light_userdata:object_to_notify_about): nothing
SelectionNotifyEnd(light_userdata:associated_context): nothing
CreateMultiPatch({light_userdata:fixture_handles}, integer:count[ ,string:undo_text]): integer:amount_of_multi-patch_fixtures_created
GlobalVars(nothing): light_userdata:global_variables
UserVars(nothing): light_userdata:user_variables
PluginVars([string:plugin_name]): light_userdata:plugin_preferences
AddonVars(string:addon_name): light_userdata:addon_variables
SetVar(light_userdata:variables, string:varname, value): boolean:success
GetVar(light_userdata:variables, string:varname): value
GetVarVersion(light_userdata:variables, string:varname): integer:version
DelVar(light_userdata:variables, string:varname): boolean:success
GetApiDescriptor(nothing): table of {string:function_name, string:arguments, string:return_values}
GetObjApiDescriptor(nothing): table of {string:function_name, string:arguments, string:return_values}
GetTextScreenLine(nothing): integer:internal line number
GetTextScreenLineCount([integer:starting internal line number]): integer:line count
GetDebugFPS(nothing): float:fps
GetSample(string:type('MEMORY', 'CPU', 'CPUTEMP', 'GPUTEMP', 'SYSTEMP', 'FANRPM')): integer:current_value_in_percent
AddFixtures({'mode'=light_userdata:dmx_mode, 'amount'=integer:amount[, 'undo'=string:undo_text][, 'parent'=light_userdata:handle][, 'insert_index'=integer:value][, 'idtype'=string:idtype][, 'cid'=string:cid][, 'fid'=string:fid][, 'name'=string:name][, 'layer'=string:layer][, 'class'=string:class][, 'patch'={table 1..8: string:address}]}): boolean:success or nothing
ClassExists(string:class_name): boolean:result
IsClassDerivedFrom(string:derived_name, string:base_name): boolean:result
GetClassDerivationLevel(string:class_name): integer:result or nothing
TextInput([string:title[, string:value[, integer:x[, integer:y]]]]): string:value
PopupInput({title:str, caller:handle, items:table:{{'str'|'int'|'lua'|'handle', name, type-dependent}...}, selectedValue:str, x:int, y:int, target:handle, render_options:{left_icon, number, right_icon}, useTopLeft:bool, properties:{prop:value}, add_args:{FilterSupport='Yes'/'No'}}): integer:selected_index, string:selected_value
Confirm([string:title [,string:message [,integer:display_index [,boolean:showCancel]]]]): boolean:result
GetDisplayByIndex(integer:display_index): light_userdata:display_handle
GetRemoteVideoInfo(nothing): integer:wingID, boolean:isExtension
GetUIObjectAtPosition(integer:display_index, {x=integer:x_position,y=integer:y_position}): light_userdata:handle to UI object or nil
DrawPointer(integer:display_index, {x=integer:x_position,y=integer:y_position}, integer:duration in ms)): nothing
WaitObjectDelete(light_userdata:handle to UIObject[, number:seconds to wait]): boolean:true on success, nil on timeout
GetFocus(nothing): light_userdata:display_handle
GetFocusDisplay(nothing): light_userdata:display_handle
GetDisplayCollect(nothing): light_userdata:handle to DisplayCollect
FindBestFocus([light_userdata:handle]): nothing
FindNextFocus([bool:backwards(false)[, int(Focus::Reason):reason(UserTabKey)]]): nothing
CloseAllOverlays(nothing): nothing
GetTopModal(nothing): light_userdata:handle to top modal overlay
GetTopOverlay(integer:display_index): light_userdata:handle to top overlay on the display
WaitModal([number:seconds to wait]): handle to modal overlay or nil on failure(timeout)
SetBlockInput(boolean:block[, boolean:show_info]): nothing
GetBlockInput(nothing): boolean:block_input
FindTexture(string:texture name): light_userdata:handle to texture found
GetScreenContent(light_userdata:handle to ScreenConfig): light_userdata:handle
MessageBox({title:string,[, string:backColor][, integer:timeout (ms)][, boolean:timeoutResultCancel][, integer:timeoutResultID][, string:icon][, string:titleTextColor][, string:messageTextColor] [, boolean:autoCloseOnInput] string:message[, integer:message_align_h(Enums.AlignmentH)][, integer:message_align_v(Enums.AlignmentV)][, integer|lightuserdata:display], commands:{array of {integer:value, string:name[, integer:order]}}, inputs:{array of {string:name, string:value, string:blackFilter, string:whiteFilter, string:vkPlugin, integer:maxTextLength[, integer:order]}}, states:{array of {string:name, boolean:state[, integer:order]}, selectors:{array of {name:string, integer:selectedValue, values:table[, type:integer 0-swipe, 1-radio][, integer:order]} }): {boolean:success, integer:result, inputs:{array of [string:name] = string:value}, states:{array of [string:name] = boolean:state}, selectors:{array of [string:name] = integer:selected-value}}
FSExtendedModeHasDots(light_userdata:handle to UIGrid (or derived), {r, c}:cell): boolean

==========================================
Object API
==========================================

ToAddr(light_userdata:handle,boolean:with_name[, boolean:use_visible_addr]): string:address
Dump(light_userdata:handle): string:information
Addr(light_userdata:handle[, light_userdata:base_handle[, boolean:force_parent-based_address[, boolean:force_commandline_index-based_address]]]): string:numeric_root_address
AddrNative(light_userdata:handle, light_userdata:base_handle[, boolean:escape_names]]): string:numeric_root_address
Index(light_userdata:handle): integer:index
Parent(light_userdata:handle): light_userdata:parent_handle
Count(light_userdata:handle): integer:child_count
MaxCount(light_userdata:handle): integer:child_count
Compare(light_userdata:handle, light_userdata:handle): boolean:is_equal, string:what_differs
Resize(light_userdata:handle, integer:size): nothing
Ptr(light_userdata:handle, integer:index(1-based)): light_userdata:child_handle
CmdlinePtr(light_userdata:handle, integer:index(1-based)): light_userdata:child_handle
Children(light_userdata:handle): {light_userdata:child_handles}
CmdlineChildren(light_userdata:handle): {light_userdata:child_handles}
CurrentChild(light_userdata:handle): light_userdata:current_child or nothing
Create(light_userdata:handle, integer:child_index(1-based)[, string:class[, light_userdata:undo]]): light_userdata:child_handle
Append(light_userdata:handle[, string:class[, light_userdata:undo[, integer:count]]]): light_userdata:child_handle
Acquire(light_userdata:handle[, string:class[, light_userdata:undo]]): light_userdata:child_handle
Aquire(light_userdata:handle[, string:class[, light_userdata:undo]]): light_userdata:child_handle
Delete(light_userdata:handle, integer:child_index(1-based)[, light_userdata:undo]): nothing
Insert(light_userdata:handle, integer:child_index(1-based)[, string:class[, light_userdata:undo[, integer:count]]]): light_userdata:child_handle
Remove(light_userdata:handle, integer:child_index(1-based)[, light_userdata:undo]): nothing
Copy(light_userdata:dst_handle, light_userdata:src_handle[, light_userdata:undo]): nothing
HasParent(light_userdata:handle, handle:object_to_check): nothing
Changed(light_userdata:handle, string:change_level_enum_name): nothing
IsEmpty(light_userdata:handle): boolean:object_is_empty
IsLocked(light_userdata:handle): boolean:object_is_locked
PrepareAccess(light_userdata:handle): nothing
Set(light_userdata:handle, string:property_name, string:property_value[, integer:override_change_level(Enums.ChangeLevel)]): nothing
SetChildren(light_userdata:handle_of_parent, string:property_name, string:property_value[, boolean:recursive (default: false)]): nothing
SetChildrenRecursive(light_userdata:handle_of_parent, string:property_name, string:property_value[, boolean:recursive (default: false)]): nothing
Get(light_userdata:handle, string:property_name[, integer:role(Enums.Roles)]): light:userdata:child or string:property (if 'role' provided - always string)
PropertyCount(light_userdata:handle): integer:property_count
PropertyName(light_userdata:handle, integer:property_index): string:property_name
PropertyType(light_userdata:handle, integer:property_index): string:property_type
PropertyInfo(light_userdata:handle, integer:property_index): {'ReadOnly'=boolean:read_only_flag, 'ExportIgnore'=boolean:export_ignore_flag, 'ImportIgnore'=boolean:import_ignore_flag, 'EnumCollection'=string:enum_collection_name}
IsValid(light_userdata:handle): boolean:result
IsClass(light_userdata:handle): boolean:result
GetClass(light_userdata:handle): string:class_name
GetChildClass(light_userdata:handle): string:class_name
GetAssignedObj(light_userdata:handle): light_userdata:handle
HasEditSettingUI(light_userdata:handle): boolean:result
HasEditUI(light_userdata:handle): boolean:result
GetUIEditor(light_userdata:handle): string:ui_editor_name
GetUISettings(light_userdata:handle): string:ui_settings_name
FindParent(light_userdata:search_start_handle, string:search_class_name): light_userdata:found_handle
Find(light_userdata:search_start_handle, string:search_name[, string:search_class_name]): light_userdata:found_handle
FindRecursive(light_userdata:search_start_handle, string:search_name[, string:search_class_name]): light_userdata:found_handle
FindWild(light_userdata:search_start_handle, string:search_name): light_userdata:found_handle
Import(light_userdata:handle, string:file_path, string:file_name): boolean:success
Export(light_userdata:handle, string:file_path, string:file_name): boolean:success
GetExportFileName(light_userdata:handle[, boolean:camel_case_to_file_name]): string:file_name
Load(light_userdata:handle, string:file_path, string:file_name): boolean:success
Save(light_userdata:handle, string:file_path, string:file_name): boolean:success
CommandCall(light_userdata:handle, light_userdata:dest_handle, boolean:focus_search_allowed(default:true)): nothing
CommandAt(light_userdata:handle): nothing
CommandDelete(light_userdata:handle): nothing
CommandStore(light_userdata:handle): nothing
CommandCreateDefaults(light_userdata:handle): nothing
SetFader(light_userdata:handle, {[float:value[0..100]], [boolean:faderEnabled], [string:token(Fader*)]}): nothing
GetFader(light_userdata:handle, {[string:token(Fader*)], [integer:index]}): float:value[0..100]
GetFaderText(light_userdata:handle, {[string:token(Fader*)], [integer:index]}): string:text
GetLineCount(light_userdata:handle): integer:count
GetLineAt(light_userdata:handle, integer:line_number): string:line_content
HasActivePlayback(light_userdata:handle): boolean:result
HasReferences(light_userdata:handle): boolean:result
HasDependencies(light_userdata:handle): boolean:result
GetReferences(light_userdata:handle): {light_userdata:handle}
GetDependencies(light_userdata:handle): {light_userdata:handle}
InputSetTitle(light_userdata:handle, string:name_value): nothing
InputSetValue(light_userdata:handle, string:value): nothing
InputSetEditTitle(light_userdata:handle, string:name_value): nothing
InputSetAdditionalParameter(light_userdata:handle, string:parameter name, string:parameter value): nothing
InputRun(light_userdata:handle): nothing
InputCallFunction(light_userdata:handle, string:function name[, ...parameters to function]): <depends on function>
InputHasFunction(light_userdata:handle, string:function name): true or nil
InputSetMaxLength(light_userdata:handle, integer:length): nothing
AddListStringItem(light_userdata:handle, string:name, string:value[, {[left={...}][right={...}]}:appearance]): nothing
AddListPropertyItem(light_userdata:handle, string:name, string:value, light_userdata:target handle[,{[left={...}][right={...}]}:appearance]): nothing
AddListNumericItem(light_userdata:handle, string:name, number:value[,light_userdata:base handle[, {[left={...}][right={...}]}:appearance]]): nothing
AddListLuaItem(light_userdata:handle, string:name, string:value/function name, lua_function:callback reference[, <any lua type>:argument to pass to callback[, {[left={...}][right={...}]}:appearance]]): nothing
AddListObjectItem(light_userdata:handle, light_userdata:target object[, (string: explicit name[, {[boolean:appearance],[left={...}][right={...}]}:appearance] | enum{Roles}: role [, :boolean: extended_name[, {[left={...}][right={...}]}:appearance],[string:postNameText])]): nothing
AddListStringItems(light_userdata:handle, table{item={[1]=name, [2]=value}, ...}): nothing
AddListPropertyItems(light_userdata:handle, table{item={[1]=name, [2]=property name, [3]=target handle}, ...}): nothing
AddListNumericItems(light_userdata:handle, table{item={[1]=name, [2]=integer:value}, ...}): nothing
AddListLuaItems(light_userdata:handle, table{item={[1]=name, [2]=value/function name, [3]=callback reference[, [4]=argument of any lua type to pass to callback]}, ...}): nothing
AddListChildren(light_userdata:handle, light_userdata:parent[, enum{Roles}:role]): nothing
AddListChildrenNames(light_userdata:handle, light_userdata:parent[, enum{Roles}:role]): nothing
AddListRecursiveNames(light_userdata:handle, light_userdata:parent[, enum{Roles}:role]): nothing
RemoveListItem(light_userdata:handle, string:name): nothing
ClearList(light_userdata:handle): nothing
SelectListItemByName(light_userdata:handle, string:name_value): nothing
SelectListItemByValue(light_userdata:handle, string:value): nothing
SelectListItemByIndex(light_userdata:handle, integer:index(1-based)): nothing
IsListItemEnabled(light_userdata:handle, integer:index): nothing
SetEnabledListItem(light_userdata:handle, integer:index[, bool:enable(default:true)]): nothing
IsListItemEmpty(light_userdata:handle, integer:index): nothing
SetEmptyListItem(light_userdata:handle, integer:index[, bool:empty(default:true)]): nothing
GetListItemValueStr(light_userdata:handle, integer:index): string:value
SetListItemValueStr(light_userdata:handle, integer:index, string:value): nothing
GetListItemValueI64(light_userdata:handle, integer:index): integer:value
GetListItemName(light_userdata:handle, integer:index): string:name
SetListItemName(light_userdata:handle, integer:index, string:name): nothing
GetListItemAppearance(light_userdata:handle, integer:index): {left={AppearanceData}, right={AppearanceData}}
SetListItemAppearance(light_userdata:handle, integer:index, {[left={...AppearanceData...}][right={...AppearanceData...}]}): nothing
GetListItemAdditionalInfo(light_userdata:handle, integer:index): string:value
SetListItemAdditionalInfo(light_userdata:handle, integer:index, string:value): nothing
GetListItemButton(light_userdata:handle, integer:index): light_userdata:button or nil if not visible
GetListSelectedItemIndex(light_userdata:handle): integer:1-based index
GetListItemsCount(light_userdata:handle): integer:amount of items in the list
FindListItemByValueStr(light_userdata:handle, string:value): integer:1-based index
FindListItemByName(light_userdata:handle, string:value): integer:1-based index
GridGetBase(light_userdata:handle to UIGrid (or derived)): light_userdata:handle to GridBase
GridGetData(light_userdata:handle to UIGrid (or derived)): light_userdata:handle to GridData
GridGetSelection(light_userdata:handle to UIGrid (or derived)): light_userdata:handle to GridSelection
GridMoveSelection(light_userdata:handle to UIGrid (or derived), x, y): nothing
GridGetSelectedCells(light_userdata:handle to UIGrid (or derived)): array of {r, c, r_UniqueId, r_GroupId, c_UniqueId, c_GroupId} cells in the selection
GridGetSettings(light_userdata:handle to UIGrid (or derived)): light_userdata:handle to GridSettings
GridGetDimensions(light_userdata:handle to UIGrid (or derived)): {r, c}
GridGetScrollOffset(light_userdata:handle to UIGrid (or derived)): {v = {index, offset}, h={index, offset}}
GridSetColumnSize(light_userdata:handle to UIGrid (or derived), integer: columnId, integer:size in pixels): nothing
GridGetScrollCell(light_userdata:handle to UIGrid (or derived)): {r, c}
GridGetCellData(light_userdata:handle to UIGrid (or derived), {r, c}:cell): {text, color={text, back}}
GridIsCellVisible(light_userdata:handle to UIGrid (or derived), {r, c}:cell): boolean
GridCellExists(light_userdata:handle to UIGrid (or derived), {r, c}:cell): boolean
GridIsCellReadOnly(light_userdata:handle to UIGrid (or derived), {r, c}:cell): boolean
GridScrollCellIntoView(light_userdata:handle to UIGrid (or derived), {r, c}:cell): nothing
GridGetCellDimensions(light_userdata:handle to UIGrid (or derived), {r, c}:cell): {x, y, w, h}
GridGetParentRowId(light_userdata:handle to UIGrid (or derived), integer: rowId): parent row id (integer) or nil (if there's no parent)
GridsGetExpandHeaderCell(light_userdata:handle to UIGrid (or derived)): {r, c} or nil
GridsGetExpandHeaderCellState(light_userdata:handle to UIGrid (or derived)): boolean or nil
GridsGetLevelButtonWidth(light_userdata:handle to UIGrid (or derived), {r, c}:cell): width in pixels or nil
GridsGetColumnById(light_userdata:handle to UIGrid (or derived), integer: columnId): column index or nil (if there's no such visible column)
GridsGetRowById(light_userdata:handle to UIGrid (or derived), integer: rowId): row index or nil (if there's no such visible row)
GetOverlay(light_userdata:handle to UIObject): light_userdata:overlay_handle
GetDisplay(light_userdata:handle to UIObject): light_userdata:display_handle
GetDisplayIndex(light_userdata:handle to UIObject): integer:display_index
GetScreen(light_userdata:handle to UIObject): light_userdata:handle
GetUIChildrenCount(light_userdata:handle to UIObject): integer:count
ClearUIChildren(light_userdata:handle to UIObject): nothing
GetUIChild(light_userdata:handle to UIObject, integer:index(1-based)): light_userdata:handle to UIObject
UIChildren(light_userdata:handle to UIObject): {light_userdata:child_handles}
WaitInit(light_userdata:handle to UIObject[, number:seconds to wait[, bool:force to re-init, default - false]]): boolean:true on success, nil on timeout or if object doesn't exist
WaitChildren(light_userdata:handle to UIObject, integer:expected amount of children[, number:seconds to wait]): boolean:true on success, nil on timeout or if object doesn't exist
HookDelete(light_userdata:handle to UIObject, function:callback to invoke on deletion[, any:argument to pass by]): boolean:true on success, nil on failure
IsVisible(light_userdata:handle to UIObject): bool:is visible
IsEnabled(light_userdata:handle to UIObject): bool:is enabled
ShowModal(light_userdata:handle, callback:function): nothing
SetPositionHint(light_userdata:handle, integer:x, integer:y): nothing
ScrollIsNeeded(light_userdata:handle, integer:scroll type (see 'ScrollType' enum)): boolean:true if scroll of the requested type is needed
ScrollDo(light_userdata:handle, integer:scroll type (see 'ScrollType' enum), integer:scroll entity (item or area, see 'ScrollParamEntity' enum), integer:value type (absolute or relative, see 'ScrollParamValueType' enum), number: value to scroll (items - 1-based), boolean: updateOpposite side): boolean:true scroll
ScrollGetInfo(light_userdata:handle, integer:scroll type (see 'ScrollType' enum)): {index(1-based), offset, visibleArea, totalArea, itemsCount, itemsOnPage} or nil
ScrollGetItemSize(light_userdata:handle, integer:scroll type (see 'ScrollType' enum), integer:1-based item idx): integer:size of the item of nil
ScrollGetItemOffset(light_userdata:handle, integer:scroll type (see 'ScrollType' enum), integer:1-based item idx): integer:offset of the item or nil
ScrollGetItemByOffset(light_userdata:handle, integer:scroll type (see 'ScrollType' enum), integer:offset): integer:1-based item index
SetContextSensHelpLink(light_userdata:handle to UIObject, string:topic name): nothing
UILGGetColumnWidth(light_userdata:handle to UILayoutGrid, integer:index): integer:size
UILGGetRowHeight(light_userdata:handle to UILayoutGrid, integer:index): integer:size
UILGGetColumnAbsXLeft(light_userdata:handle to UILayoutGrid, integer:index): integer:x
UILGGetColumnAbsXRight(light_userdata:handle to UILayoutGrid, integer:index): integer:x
UILGGetRowAbsYTop(light_userdata:handle to UILayoutGrid, integer:index): integer:y
UILGGetRowAbsYBottom(light_userdata:handle to UILayoutGrid, integer:index): integer:y
OverlaySetCloseCallback(light_userdata:handle to Overlay, callbackName:string[, ctx:anything]): nothing
FSExtendedModeHasDots(light_userdata:handle to UIGrid (or derived), {r, c}:cell): boolean
