--[[
================================================================================
grandMA3 MCP Plugin - Lighting Control Bridge
================================================================================

This plugin provides a file-based interface between the grandMA3 console 
and external applications using MCP (Model Context Protocol).

Communication uses platform-specific shared directories:
  macOS:   /Users/Shared/MA3/
  Windows: C:/ProgramData/MA3/

Files:
  - mcp_command.txt  : Commands from MCP client
  - mcp_response.txt : Responses from this plugin

The plugin runs in the background, polling for command files and executing
them safely within the grandMA3 environment.

Version: 2.0
Lua Version: 5.4.4
MA3 Version: 2.0+

Repository: https://github.com/Pahegi/MA3-MCP-Server
================================================================================
--]]


-- =============================================================================
-- CONFIGURATION & FILE I/O
-- =============================================================================

-- Platform detection and path configuration
local function getIpcDirectory()
    -- Check for environment override first (via MA3 plugin variables if available)
    -- Otherwise use platform-specific defaults
    
    local sep = package.config:sub(1,1)  -- "/" on Unix, "\" on Windows
    
    if sep == "/" then
        -- Unix-like (macOS)
        -- Check if /Users/Shared exists (macOS)
        local f = io.open("/Users/Shared/.exists_check", "w")
        if f then
            f:close()
            os.remove("/Users/Shared/.exists_check")
            return "/Users/Shared/MA3"
        else
            error("Unsupported platform: Unix-like system without /Users/Shared directory")
        end
    else
        -- Windows
        return "C:/ProgramData/MA3"
    end
end

local IPC_DIR = getIpcDirectory()
local COMMAND_FILE = IPC_DIR .. "/mcp_command.txt"
local RESPONSE_FILE = IPC_DIR .. "/mcp_response.txt"
local AUTOLOAD_FILE = IPC_DIR .. "/mcp_autoload.txt"
local lastRequestId = ""

local function log(msg)
    Printf("MCP: " .. tostring(msg))
end

local function readFile(path)
    local f = io.open(path, "r")
    if not f then return nil end
    local content = f:read("*all")
    f:close()
    return content
end

local function writeFile(path, content)
    local f = io.open(path, "w")
    if not f then
        log("Failed to open file for writing: " .. path)
        return false
    end
    f:write(content)
    f:close()
    return true
end

local function parseCommand(raw)
    if not raw or raw == "" then return nil, nil end
    
    -- Trim whitespace
    raw = raw:match("^%s*(.-)%s*$")
    if raw == "" then return nil, nil end
    
    -- Find colon separator between request ID and command
    local colonPos = raw:find(":")
    if not colonPos then return nil, raw end
    
    local requestId = raw:sub(1, colonPos - 1)
    local command = raw:sub(colonPos + 1)
    return requestId, command
end

-- Serialize a value to JSON-like string (no limits for local communication)
local function serialize(val, depth)
    depth = depth or 0
    if depth > 10 then return '"..."' end
    
    local t = type(val)
    if t == "nil" then
        return "null"
    elseif t == "boolean" then
        return val and "true" or "false"
    elseif t == "number" then
        return tostring(val)
    elseif t == "string" then
        -- Check for "None" string which is MA3's way of saying nil
        if val == "None" then
            return "null"
        end
        return '"' .. val:gsub('"', '\\"'):gsub("\n", "\\n") .. '"'
    elseif t == "table" then
        local parts = {}
        local isArray = #val > 0
        for k, v in pairs(val) do
            if isArray then
                table.insert(parts, serialize(v, depth + 1))
            else
                table.insert(parts, '"' .. tostring(k) .. '":' .. serialize(v, depth + 1))
            end
        end
        if isArray then
            return "[" .. table.concat(parts, ",") .. "]"
        else
            return "{" .. table.concat(parts, ",") .. "}"
        end
    elseif t == "userdata" then
        -- MA3 handle - get name and address
        local info = {}
        local success, name = pcall(function() return val.name end)
        if success and name then
            info.name = tostring(name)
        end
        local success2, addr = pcall(function() return val:Addr() end)
        if success2 and addr then
            info.addr = tostring(addr)
        end
        if info.name or info.addr then
            return serialize(info, depth + 1)
        end
        return '"[handle]"'
    else
        return '"[' .. t .. ']"'
    end
end

-- Get object by address using MA3's GetObject
local function getObjectByAddress(address)
    -- Some addresses crash GetObject, so we need to be extra careful
    local obj = nil
    local success, err = pcall(function()
        obj = GetObject(address)
    end)
    if success and obj then
        return obj, nil
    elseif not success then
        return nil, "GetObject error: " .. tostring(err)
    else
        return nil, "Object not found: " .. address
    end
end

-- Get object info - list children with names
local function getObjectInfo(obj)
    local results = {}
    
    -- Get basic info
    local success, name = pcall(function() return obj.name end)
    if success and name then
        table.insert(results, "Name: " .. tostring(name))
    end
    
    local success2, addr = pcall(function() return obj:Addr() end)
    if success2 and addr then
        table.insert(results, "Addr: " .. tostring(addr))
    end
    
    local success3, class = pcall(function() return obj:GetClass() end)
    if success3 and class then
        table.insert(results, "Class: " .. tostring(class))
    end
    
    -- Get child count
    local success4, count = pcall(function() return obj:Count() end)
    if success4 and count then
        table.insert(results, "Children: " .. tostring(count))
        
        -- List children (no limit)
        if count > 0 then
            table.insert(results, "---")
            for i = 1, count do
                local success5, child = pcall(function() return obj:Ptr(i) end)
                if success5 and child then
                    local childName = ""
                    local sn, n = pcall(function() return child.name end)
                    if sn and n then
                        childName = tostring(n)
                    end
                    local childNo = ""
                    local sno, no = pcall(function() return child.no end)
                    if sno and no then
                        childNo = tostring(no)
                    end
                    table.insert(results, i .. ": [" .. childNo .. "] " .. childName)
                end
            end
        end
    end
    
    return table.concat(results, "\n")
end

-- Get property value from an object
local function getPropertyValue(obj, propName)
    local success, value = pcall(function()
        return obj:Get(propName)
    end)
    if success and value ~= nil then
        if type(value) == "userdata" then
            local sn, n = pcall(function() return value.name end)
            if sn and n then
                return tostring(n)
            end
            return "[handle]"
        elseif type(value) == "number" then
            return tostring(value)
        elseif type(value) == "boolean" then
            return value and "true" or "false"
        else
            return tostring(value)
        end
    else
        return nil
    end
end

-- Get all properties of an object as a table
local function getAllProperties(obj)
    local props = {}
    local success, count = pcall(function() return obj:PropertyCount() end)
    if success and count then
        -- PropertyName is 0-based in MA3 API
        for i = 0, count - 1 do
            local sn, name = pcall(function() return obj:PropertyName(i) end)
            if sn and name then
                local sv, value = pcall(function() return obj:Get(name) end)
                if sv and value ~= nil then
                    -- Store with uppercase key for consistent access
                    local upperName = string.upper(name)
                    if type(value) == "userdata" then
                        local shn, hn = pcall(function() return value.name end)
                        if shn and hn then
                            props[upperName] = tostring(hn)
                        else
                            props[upperName] = "[handle]"
                        end
                    elseif type(value) == "number" then
                        props[upperName] = value
                    elseif type(value) == "boolean" then
                        props[upperName] = value
                    else
                        props[upperName] = tostring(value)
                    end
                end
            end
        end
    end
    return props
end


-- =============================================================================
-- OBJECT QUERY HANDLERS
-- =============================================================================

-- Handle query command (prefix "?") - query object by address
local function handleQuery(query)
    local obj, err = getObjectByAddress(query)
    if not obj then
        return nil, err
    end
    return getObjectInfo(obj), nil
end

-- Handle get command (prefix "get:") - get property from object
local function handleGet(query)
    -- Format: "address.property" or "address property"
    local address, prop = query:match("^(.+)%.([^%.]+)$")
    if not address then
        address, prop = query:match("^(.+)%s+([^%s]+)$")
    end
    if not address or not prop then
        return nil, "Format: get:address.property or get:address property"
    end
    
    local obj, err = getObjectByAddress(address)
    if not obj then
        return nil, err
    end
    
    local value = getPropertyValue(obj, prop)
    if value then
        return value, nil
    else
        return nil, "Property not found: " .. prop
    end
end

-- Handle props command (prefix "props:") - get ALL properties of an object
local function handleProps(address)
    local obj, err = getObjectByAddress(address)
    if not obj then
        return nil, err
    end
    
    local props = getAllProperties(obj)
    return serialize(props), nil
end

-- Handle children command (prefix "children:") - list children of object
local function handleChildren(address)
    local obj, err = getObjectByAddress(address)
    if not obj then
        return nil, err
    end
    
    local results = {}
    local success, count = pcall(function() return obj:Count() end)
    if success and count then
        for i = 1, count do
            local sc, child = pcall(function() return obj:Ptr(i) end)
            if sc and child then
                local name = ""
                local sn, n = pcall(function() return child.name end)
                if sn and n then name = tostring(n) end
                local no = ""
                local sno, nno = pcall(function() return child.no end)
                if sno and nno then no = tostring(nno) end
                table.insert(results, no .. ": " .. name)
            end
        end
    end
    
    return table.concat(results, "\n"), nil
end

-- Handle getattr command (prefix "getattr:") - get fixture attribute value
-- Format: getattr:fixture_id attribute_name
-- Example: getattr:1 Dimmer
-- NOTE: fixture_id is the FID (fixture ID), not the patch index!
local function handleGetAttr(query)
    -- Parse fixture ID and attribute name
    local fixId, attrName = query:match("^(%d+)%s+(.+)$")
    if not fixId or not attrName then
        return nil, "Format: getattr:fixture_id attribute_name (e.g., getattr:1 Dimmer)"
    end
    
    fixId = tonumber(fixId)
    attrName = attrName:match("^%s*(.-)%s*$")  -- trim
    
    local results = {}
    results.fixture_id = fixId
    results.attribute = attrName
    
    -- Use ObjectList to get the fixture by ID (this works with FID)
    local success1, fixtures = pcall(function()
        return ObjectList("Fixture " .. tostring(fixId))
    end)
    
    if not success1 or not fixtures or #fixtures == 0 then
        return nil, "Fixture " .. tostring(fixId) .. " not found"
    end
    
    local fixture = fixtures[1]
    results.fixture_name = fixture.name
    results.patch = fixture.patch
    
    -- Get the attribute index
    local attrIdx = GetAttributeIndex(attrName)
    if attrIdx == nil then
        return nil, "Unknown attribute: " .. attrName
    end
    results.attribute_index = attrIdx
    
    -- Get the patch index for this fixture
    local subfixtureCount = GetSubfixtureCount()
    
    local patchIdx = nil
    for i = 0, subfixtureCount - 1 do
        local sf = GetSubfixture(i)
        if sf then
            local sfid = nil
            local s, fid = pcall(function() return sf.fid end)
            if s and fid then sfid = fid end
            if not sfid then
                local s2, no = pcall(function() return sf.no end)
                if s2 and no then sfid = no end
            end
            if sfid == fixId then
                patchIdx = i
                break
            end
        end
    end
    
    if patchIdx == nil then
        patchIdx = fixId - 1
        results.patch_idx_guessed = true
    end
    results.patch_index = patchIdx
    
    -- Get UI Channel index for this fixture and attribute
    local uiChIdx = nil
    local success2, uiChIdxResult = pcall(function()
        return GetUIChannelIndex(patchIdx, attrIdx)
    end)
    
    if success2 and uiChIdxResult ~= nil then
        uiChIdx = uiChIdxResult
        results.ui_channel_index = uiChIdx
        
        -- Use GetUIChannel to get a proper table descriptor (not handles)
        local successUiCh, uiChDescriptor = pcall(function()
            return GetUIChannel(uiChIdx, attrIdx)
        end)
        if successUiCh and uiChDescriptor and type(uiChDescriptor) == "table" then
            results.ui_channel_data = {}
            for k, v in pairs(uiChDescriptor) do
                if type(v) ~= "function" then
                    if type(v) == "userdata" then
                        local sn, n = pcall(function() return v.name end)
                        if sn and n then 
                            results.ui_channel_data[k] = tostring(n)
                        end
                    elseif type(v) == "table" then
                        -- Nested table - serialize carefully
                        results.ui_channel_data[k] = {}
                        for k2, v2 in pairs(v) do
                            if type(v2) ~= "function" and type(v2) ~= "userdata" then
                                results.ui_channel_data[k][k2] = v2
                            end
                        end
                    else
                        results.ui_channel_data[k] = v
                    end
                end
            end
        end
        
        -- GetProgPhaser returns programmer values - the 'absolute' field contains current value
        -- phaser_only=false means we get ALL data including static values
        local successProg, progData = pcall(function()
            return GetProgPhaser(uiChIdx, false)
        end)
        if successProg and progData and type(progData) == "table" then
            results.programmer = {}
            -- Extract key fields
            if progData.absolute ~= nil then results.programmer.absolute = progData.absolute end
            if progData.absolute_value ~= nil then results.programmer.absolute_value = progData.absolute_value end
            if progData.relative ~= nil then results.programmer.relative = progData.relative end
            if progData.fade ~= nil then results.programmer.fade = progData.fade end
            if progData.delay ~= nil then results.programmer.delay = progData.delay end
            if progData.mask_active_value ~= nil then results.programmer.mask_active_value = progData.mask_active_value end
            if progData.channel_function ~= nil then results.programmer.channel_function = progData.channel_function end
            
            -- Check for nested step data (array part of progData)
            for i = 1, 10 do
                if progData[i] and type(progData[i]) == "table" then
                    results.programmer["step" .. i] = {}
                    local step = progData[i]
                    if step.absolute ~= nil then results.programmer["step" .. i].absolute = step.absolute end
                    if step.absolute_value ~= nil then results.programmer["step" .. i].absolute_value = step.absolute_value end
                    if step.relative ~= nil then results.programmer["step" .. i].relative = step.relative end
                    if step.channel_function ~= nil then results.programmer["step" .. i].channel_function = step.channel_function end
                end
            end
        end
    end
    
    -- Try to get RT channels for DMX patch info
    local success4, rtChannels = pcall(function()
        return GetRTChannels(patchIdx, false)  -- false = return indices, not handles
    end)
    
    if success4 and rtChannels and #rtChannels > 0 then
        results.rt_channel_count = #rtChannels
        
        -- Get info from the first RT channel
        local rtIdx = rtChannels[1]
        local success5, rtInfo = pcall(function()
            return GetRTChannel(rtIdx)
        end)
        
        if success5 and rtInfo and type(rtInfo) == "table" then
            results.dmx_default = rtInfo.dmx_default
            results.dmx_highlight = rtInfo.dmx_highlight
            results.rt_index = rtInfo.rt_index
            
            -- Get patch info if available
            if rtInfo.patch and type(rtInfo.patch) == "table" then
                results.dmx_address = rtInfo.patch.address
                results.dmx_universe = rtInfo.patch.universe
            end
        end
    end
    
    -- Try to get DMX output value directly using fixture's patch address
    if results.dmx_universe and results.dmx_address then
        local successDmx, dmxVal = pcall(function()
            return GetDMXValue(results.dmx_address, results.dmx_universe, true)
        end)
        if successDmx and dmxVal ~= nil then
            results.dmx_output_percent = dmxVal
        end
    end
    
    return serialize(results), nil
end

-- Handle listattr command (prefix "listattr:") - list all attributes of a fixture
-- Format: listattr:fixture_id
-- Example: listattr:1
local function handleListAttr(query)
    local fixId = tonumber(query)
    if not fixId then
        return nil, "Format: listattr:fixture_id (e.g., listattr:1)"
    end
    
    -- Get the patch index for this fixture
    local subfixtureCount = GetSubfixtureCount()
    local patchIdx = nil
    
    for i = 0, subfixtureCount - 1 do
        local sf = GetSubfixture(i)
        if sf then
            local sfid = nil
            local s, fid = pcall(function() return sf.fid end)
            if s and fid then sfid = fid end
            if not sfid then
                local s2, no = pcall(function() return sf.no end)
                if s2 and no then sfid = no end
            end
            if sfid == fixId then
                patchIdx = i
                break
            end
        end
    end
    
    if patchIdx == nil then
        patchIdx = fixId - 1
    end
    
    -- Get UI channels with handles
    local success, uiChannels = pcall(function()
        return GetUIChannels(patchIdx, true)
    end)
    
    if not success or not uiChannels then
        return nil, "Could not get UI channels for fixture " .. tostring(fixId)
    end
    
    local results = {
        fixture_id = fixId,
        patch_index = patchIdx,
        attributes = {}
    }
    
    for _, ch in ipairs(uiChannels) do
        local attrInfo = {}
        
        -- Get attribute name via GetAttributeByUIChannel
        if ch.INDEX then
            local sa, attr = pcall(function()
                return GetAttributeByUIChannel(ch.INDEX - 1)
            end)
            if sa and attr then
                local sn, n = pcall(function() return attr.name end)
                if sn and n then attrInfo.name = tostring(n) end
            end
        end
        
        -- Get subattribute
        if ch.SUBATTRIBUTE then
            attrInfo.subattribute = ch.SUBATTRIBUTE
        end
        
        -- Get UI channel index
        if ch.INDEX then
            attrInfo.ui_index = ch.INDEX - 1
        end
        
        table.insert(results.attributes, attrInfo)
    end
    
    return serialize(results), nil
end


-- =============================================================================
-- FIXTURE & ATTRIBUTE HANDLERS
-- =============================================================================

-- Handle listfix command (prefix "listfix:") - list all patched fixtures
-- Format: listfix: (no arguments needed)
-- Returns all patched fixtures with their FID, name, and patch address
local function handleListFix(query)
    local results = {
        fixtures = {}
    }
    
    local subfixtureCount = GetSubfixtureCount()
    results.total_count = subfixtureCount
    
    -- No limit for local communication
    for i = 0, subfixtureCount - 1 do
        local sf = GetSubfixture(i)
        if sf then
            local fixData = {
                patch_index = i
            }
            
            -- Get name
            local sn, n = pcall(function() return sf.name end)
            if sn and n and n ~= nil then fixData.name = tostring(n) end
            
            -- Get FID (fixture ID) - only include if it's a real number
            local sfid, fid = pcall(function() return sf.fid end)
            if sfid and fid and type(fid) == "number" then 
                fixData.fid = fid 
            end
            
            -- Get fixture number
            local sno, no = pcall(function() return sf.no end)
            if sno and no and type(no) == "number" then 
                fixData.no = no 
            end
            
            -- Get patch address
            local sp, p = pcall(function() return sf.patch end)
            if sp and p and p ~= "" then 
                fixData.patch = tostring(p) 
            end
            
            -- Get CID (channel ID) - only include if it's a real number
            local scid, cid = pcall(function() return sf.cid end)
            if scid and cid and type(cid) == "number" then 
                fixData.cid = cid 
            end
            
            table.insert(results.fixtures, fixData)
        end
    end
    
    return serialize(results), nil
end


-- =============================================================================
-- DMX HANDLERS
-- =============================================================================

-- Handle getdmx command (prefix "getdmx:") - get DMX output value
-- Format: getdmx:address [universe]
-- Example: getdmx:1 or getdmx:1 1
local function handleGetDMX(query)
    local addr, universe = query:match("^(%d+)%s*(%d*)$")
    if not addr then
        return nil, "Format: getdmx:address [universe] (e.g., getdmx:1 or getdmx:1 1)"
    end
    
    addr = tonumber(addr)
    universe = tonumber(universe) or 1
    
    -- Try GetDMXUniverse first (gets entire universe as table)
    local success1, dmxTable = pcall(function()
        return GetDMXUniverse(universe, true)  -- true = percent mode
    end)
    
    if success1 and dmxTable and dmxTable[addr] ~= nil then
        local results = {
            address = addr,
            universe = universe,
            value_percent = dmxTable[addr]
        }
        return serialize(results), nil
    end
    
    -- Fallback: Try GetDMXValue
    local success2, value = pcall(function()
        return GetDMXValue(addr, universe, true)
    end)
    if success2 and value ~= nil then
        return tostring(value), nil
    end
    
    -- Try without percent mode
    local success3, value3 = pcall(function()
        return GetDMXValue(addr, universe, false)
    end)
    if success3 and value3 ~= nil then
        return tostring(value3), nil
    end
    
    -- Try to get DMX universe object
    local dmxUniverse, err = getObjectByAddress("DMX " .. tostring(universe))
    if dmxUniverse then
        local results = {}
        results.universe = universe
        results.address = addr
        
        local sn, n = pcall(function() return dmxUniverse.name end)
        if sn and n then results.universeName = tostring(n) end
        
        -- Try to get the channel
        local sc, ch = pcall(function() return dmxUniverse:Ptr(addr) end)
        if sc and ch then
            local sv, v = pcall(function() return ch.value end)
            if sv and v then
                results.value = v
                return serialize(results), nil
            end
        end
        
        return serialize(results), nil
    end
    
    return nil, "Could not get DMX value for address " .. tostring(addr) .. " universe " .. tostring(universe)
end

-- Handle getprog command (prefix "getprog:") - get programmer values for fixture
-- Format: getprog:fixture_index [attribute_name]
local function handleGetProg(query)
    local fixIdx, attrName = query:match("^(%d+)%s*(.*)$")
    if not fixIdx then
        return nil, "Format: getprog:fixture_index [attribute_name]"
    end
    
    fixIdx = tonumber(fixIdx)
    
    -- Try to get Programmer object
    local programmer, err = getObjectByAddress("Programmer")
    if not programmer then
        return nil, "Could not access Programmer: " .. tostring(err)
    end
    
    local results = {}
    results.fixture = fixIdx
    
    -- Get programmer info
    local sn, n = pcall(function() return programmer.name end)
    if sn and n then results.programmerName = tostring(n) end
    
    local sc, cnt = pcall(function() return programmer:Count() end)
    if sc and cnt then 
        results.programmerChildCount = cnt
        -- List first few children to understand structure
        results.children = {}
        for i = 1, math.min(cnt, 10) do
            local sch, ch = pcall(function() return programmer:Ptr(i) end)
            if sch and ch then
                local info = {}
                local scn, cn = pcall(function() return ch.name end)
                if scn and cn then info.name = tostring(cn) end
                local sca, ca = pcall(function() return ch:Addr() end)
                if sca and ca then info.addr = tostring(ca) end
                local scc, cc = pcall(function() return ch:GetClass() end)
                if scc and cc then info.class = tostring(cc) end
                table.insert(results.children, info)
            end
        end
    end
    
    -- Try to get fixture from programmer specifically
    local fixPath = "Programmer.Fixture " .. tostring(fixIdx)
    local progFix, err2 = getObjectByAddress(fixPath)
    if progFix then
        results.fixtureInProgrammer = true
        local sfn, fn = pcall(function() return progFix.name end)
        if sfn and fn then results.fixtureName = tostring(fn) end
    else
        results.fixtureInProgrammer = false
    end
    
    return serialize(results), nil
end

-- Handle dmxuni command (prefix "dmxuni:") - get all non-zero DMX values in a universe
-- Format: dmxuni:universe
-- Example: dmxuni:1
local function handleDMXUniverse(query)
    local universe = tonumber(query)
    if not universe then
        universe = 1
    end
    
    local success, dmxTable = pcall(function()
        return GetDMXUniverse(universe, true)  -- true = percent mode
    end)
    
    if not success or not dmxTable then
        return nil, "Could not get DMX universe " .. tostring(universe) .. " - may not be granted"
    end
    
    -- Return only non-zero values to keep response small
    local results = {
        universe = universe,
        values = {}
    }
    
    for addr, value in ipairs(dmxTable) do
        if value > 0 then
            results.values[tostring(addr)] = value
        end
    end
    
    return serialize(results), nil
end

-- Handle listprog command (prefix "listprog:") - list all programmer contents
-- Format: listprog: (no arguments needed)
-- Returns all fixtures and their attribute values currently in the programmer
local function handleListProg(query)
    local results = {
        fixtures = {}
    }
    
    -- Get selection count
    local selCount = SelectionCount()
    results.selection_count = selCount
    
    if selCount == 0 then
        return serialize(results), nil
    end
    
    -- Iterate through all selected fixtures (no limit)
    local idx = SelectionFirst()
    local fixtureNum = 0
    
    while idx ~= nil do
        fixtureNum = fixtureNum + 1
        local fixtureData = {
            patch_index = idx,
            attributes = {}
        }
        
        -- Get subfixture info
        local sf = GetSubfixture(idx)
        if sf then
            local sn, n = pcall(function() return sf.name end)
            if sn and n then fixtureData.name = tostring(n) end
            local sfid, fid = pcall(function() return sf.fid end)
            if sfid and fid then fixtureData.fid = fid end
            local sno, no = pcall(function() return sf.no end)
            if sno and no then fixtureData.no = no end
        end
        
        -- Get all UI channels for this fixture
        local successUi, uiChannels = pcall(function()
            return GetUIChannels(idx, true)  -- true = return handles
        end)
        
        if successUi and uiChannels then
            for _, ch in ipairs(uiChannels) do
                if ch.INDEX then
                    local uiChIdx = ch.INDEX - 1
                    
                    -- Get attribute name
                    local attrName = nil
                    local sa, attr = pcall(function()
                        return GetAttributeByUIChannel(uiChIdx)
                    end)
                    if sa and attr then
                        local san, an = pcall(function() return attr.name end)
                        if san and an then attrName = tostring(an) end
                    end
                    
                    -- Get programmer value for this UI channel
                    local successProg, progData = pcall(function()
                        return GetProgPhaser(uiChIdx, false)
                    end)
                    
                    if successProg and progData and type(progData) == "table" then
                        -- Check if there's actually a value in the programmer
                        local hasValue = false
                        local value = nil
                        local valueRaw = nil
                        
                        -- Check step1 first (most common for static values)
                        if progData[1] and type(progData[1]) == "table" then
                            if progData[1].absolute ~= nil then
                                hasValue = true
                                value = progData[1].absolute
                                valueRaw = progData[1].absolute_value
                            end
                        end
                        
                        -- Also check top-level absolute
                        if not hasValue and progData.absolute ~= nil then
                            hasValue = true
                            value = progData.absolute
                            valueRaw = progData.absolute_value
                        end
                        
                        -- Check mask to see if value is active
                        if progData.mask_active_value and progData.mask_active_value > 0 then
                            hasValue = true
                        end
                        
                        if hasValue then
                            local attrData = {
                                name = attrName or ch.SUBATTRIBUTE or ("UIChannel_" .. uiChIdx),
                                ui_channel = uiChIdx
                            }
                            if value ~= nil then attrData.value = value end
                            if valueRaw ~= nil then attrData.value_raw = valueRaw end
                            if ch.SUBATTRIBUTE then attrData.subattribute = ch.SUBATTRIBUTE end
                            
                            table.insert(fixtureData.attributes, attrData)
                        end
                    end
                end
            end
        end
        
        -- Only add fixture if it has attributes in programmer
        if #fixtureData.attributes > 0 then
            table.insert(results.fixtures, fixtureData)
        end
        
        -- Move to next selected fixture
        idx = SelectionNext(idx)
    end
    
    results.fixture_count = #results.fixtures
    
    return serialize(results), nil
end


-- =============================================================================
-- SELECTION & FIXTURE CONTROL HANDLERS
-- =============================================================================

-- Handle getselection command - get currently selected fixtures
local function handleGetSelection(query)
    local results = {
        fixtures = {}
    }
    
    local selCount = SelectionCount()
    results.count = selCount
    
    if selCount == 0 then
        return serialize(results), nil
    end
    
    local idx = SelectionFirst()
    while idx ~= nil do
        local fixtureData = {
            patch_index = idx
        }
        
        local sf = GetSubfixture(idx)
        if sf then
            local sn, n = pcall(function() return sf.name end)
            if sn and n then fixtureData.name = tostring(n) end
            local sfid, fid = pcall(function() return sf.fid end)
            if sfid and fid then fixtureData.fid = fid end
            local sno, no = pcall(function() return sf.no end)
            if sno and no then fixtureData.no = no end
        end
        
        table.insert(results.fixtures, fixtureData)
        idx = SelectionNext(idx)
    end
    
    return serialize(results), nil
end

-- Handle select command - select fixtures, REPLACING current selection
-- Format: select:fixture_spec
-- Examples: select:1 Thru 10, select:Group 1, select:Clear
local function handleSelect(query)
    query = query:match("^%s*(.-)%s*$")  -- trim
    
    if query == "" or query:lower() == "clear" then
        Cmd("ClearSelection")
        return serialize({status = "OK", action = "cleared", count = 0}), nil
    end
    
    -- Clear selection first, then select new fixtures
    Cmd("ClearSelection")
    
    -- Determine command based on input (case-insensitive check for Group)
    local selectCmd
    local lowerQuery = query:lower()
    if lowerQuery:match("^group") or lowerQuery:match("^all") then
        -- Use as-is for group names like "Group 1" or "Group ALL MAC"
        selectCmd = query
    else
        -- Assume fixture numbers/range
        selectCmd = "Fixture " .. query
    end
    
    local cmdResult = Cmd(selectCmd)
    
    local selCount = SelectionCount()
    local results = {
        status = selCount > 0 and "OK" or "FAILED",
        selection = query,
        command_used = selectCmd,
        command_result = cmdResult,
        count = selCount
    }
    
    return serialize(results), nil
end

-- Handle setattr command - set attribute on CURRENT SELECTION
-- Format: setattr:attribute_name value
-- Example: setattr:Dimmer 50
local function handleSetAttr(query)
    local attrName, value = query:match("^(%S+)%s+(.+)$")
    if not attrName or not value then
        return nil, "Format: setattr:attribute value (e.g., setattr:Dimmer 50)"
    end
    
    value = tonumber(value)
    attrName = attrName:match("^%s*(.-)%s*$")  -- trim
    
    if not value then
        return nil, "Value must be a number (0-100 for percent)"
    end
    
    -- Get attribute index
    local attrIdx = GetAttributeIndex(attrName)
    if attrIdx == nil then
        return nil, "Unknown attribute: " .. attrName
    end
    
    local selCount = SelectionCount()
    if selCount == 0 then
        return nil, "No fixtures selected. Use select: first."
    end
    
    local results = {
        attribute = attrName,
        value = value,
        fixtures_set = 0,
        selection_count = selCount,
        errors = {}
    }
    
    -- Iterate through selection and set attribute on each
    local idx = SelectionFirst()
    while idx ~= nil do
        local successUi, uiChIdx = pcall(function()
            return GetUIChannelIndex(idx, attrIdx)
        end)
        
        if successUi and uiChIdx then
            local successSet, errSet = pcall(function()
                SetProgPhaser(uiChIdx, { {absolute = value} })
            end)
            
            if successSet then
                results.fixtures_set = results.fixtures_set + 1
            else
                table.insert(results.errors, "Patch " .. tostring(idx) .. ": " .. tostring(errSet))
            end
        end
        
        idx = SelectionNext(idx)
    end
    
    results.status = results.fixtures_set > 0 and "OK" or "FAILED"
    
    return serialize(results), nil
end

-- Handle setcolor command - set RGB color on CURRENT SELECTION
-- Format: setcolor:r g b
-- Example: setcolor:100 50 25
local function handleSetColor(query)
    local parts = {}
    for part in query:gmatch("%S+") do
        table.insert(parts, part)
    end
    
    if #parts < 3 then
        return nil, "Format: setcolor:r g b (e.g., setcolor:100 50 25)"
    end
    
    local r = tonumber(parts[1])
    local g = tonumber(parts[2])
    local b = tonumber(parts[3])
    
    if not r or not g or not b then
        return nil, "RGB values must be numbers (0-100)"
    end
    
    -- Get attribute indices
    local attrIdxR = GetAttributeIndex("ColorRGB_R")
    local attrIdxG = GetAttributeIndex("ColorRGB_G")
    local attrIdxB = GetAttributeIndex("ColorRGB_B")
    
    if not attrIdxR or not attrIdxG or not attrIdxB then
        return nil, "ColorRGB attributes not found in show"
    end
    
    local selCount = SelectionCount()
    if selCount == 0 then
        return nil, "No fixtures selected. Use select: first."
    end
    
    local results = {
        r = r,
        g = g,
        b = b,
        fixtures_set = 0,
        selection_count = selCount,
        errors = {}
    }
    
    -- Iterate through selection and set color on each
    local idx = SelectionFirst()
    while idx ~= nil do
        local setCount = 0
        
        -- Set R
        local successR, uiChIdxR = pcall(function() return GetUIChannelIndex(idx, attrIdxR) end)
        if successR and uiChIdxR then
            local sr, _ = pcall(function() SetProgPhaser(uiChIdxR, { {absolute = r} }) end)
            if sr then setCount = setCount + 1 end
        end
        
        -- Set G
        local successG, uiChIdxG = pcall(function() return GetUIChannelIndex(idx, attrIdxG) end)
        if successG and uiChIdxG then
            local sg, _ = pcall(function() SetProgPhaser(uiChIdxG, { {absolute = g} }) end)
            if sg then setCount = setCount + 1 end
        end
        
        -- Set B
        local successB, uiChIdxB = pcall(function() return GetUIChannelIndex(idx, attrIdxB) end)
        if successB and uiChIdxB then
            local sb, _ = pcall(function() SetProgPhaser(uiChIdxB, { {absolute = b} }) end)
            if sb then setCount = setCount + 1 end
        end
        
        if setCount > 0 then
            results.fixtures_set = results.fixtures_set + 1
        end
        
        idx = SelectionNext(idx)
    end
    
    results.status = results.fixtures_set > 0 and "OK" or "FAILED"
    
    return serialize(results), nil
end

-- Handle listgroups command (prefix "listgroups:") - list all groups
-- Format: listgroups:
local function handleListGroups(query)
    local results = {
        groups = {}
    }
    
    -- Iterate through group numbers (1-9999 but stop after 10 consecutive empty)
    local emptyCount = 0
    local groupNum = 1
    
    while emptyCount < 10 and groupNum <= 9999 do
        local grp, err = getObjectByAddress("Group " .. tostring(groupNum))
        
        if grp then
            local grpData = {
                no = groupNum
            }
            
            local sn, n = pcall(function() return grp.name end)
            if sn and n and n ~= "" then 
                grpData.name = tostring(n) 
                table.insert(results.groups, grpData)
            end
            
            emptyCount = 0
        else
            emptyCount = emptyCount + 1
        end
        
        groupNum = groupNum + 1
    end
    
    results.total_count = #results.groups
    
    return serialize(results), nil
end


-- =============================================================================
-- PROGRAMMER & CUE INSPECTION HANDLERS
-- =============================================================================

-- Handle progdetail command (prefix "progdetail:") - detailed programmer contents
-- Returns all fixtures with ALL their attribute values (not just presence)
local function handleProgDetail(query)
    local results = {
        fixtures = {},
        total_fixtures = 0,
        total_attributes = 0
    }
    
    local selCount = SelectionCount()
    results.selection_count = selCount
    
    if selCount == 0 then
        results.warning = "No fixtures selected - programmer appears empty"
        return serialize(results), nil
    end
    
    -- Iterate through all selected fixtures
    local idx = SelectionFirst()
    
    while idx ~= nil do
        local fixtureData = {
            patch_index = idx,
            attributes = {}
        }
        
        -- Get subfixture info
        local sf = GetSubfixture(idx)
        if sf then
            local sn, n = pcall(function() return sf.name end)
            if sn and n then fixtureData.name = tostring(n) end
            local sfid, fid = pcall(function() return sf.fid end)
            if sfid and fid then fixtureData.fid = fid end
            local sno, no = pcall(function() return sf.no end)
            if sno and no then fixtureData.no = no end
        end
        
        -- Get all UI channels for this fixture
        local successUi, uiChannels = pcall(function()
            return GetUIChannels(idx, true)
        end)
        
        if successUi and uiChannels then
            for _, ch in ipairs(uiChannels) do
                if ch.INDEX then
                    local uiChIdx = ch.INDEX - 1
                    
                    -- Get attribute name
                    local attrName = nil
                    local sa, attr = pcall(function()
                        return GetAttributeByUIChannel(uiChIdx)
                    end)
                    if sa and attr then
                        local san, an = pcall(function() return attr.name end)
                        if san and an then attrName = tostring(an) end
                    end
                    
                    -- Get programmer value for this UI channel
                    local successProg, progData = pcall(function()
                        return GetProgPhaser(uiChIdx, false)
                    end)
                    
                    if successProg and progData and type(progData) == "table" then
                        local hasValue = false
                        local value = nil
                        local valueRaw = nil
                        local fade = nil
                        local delay = nil
                        
                        -- Check step1 first (most common for static values)
                        if progData[1] and type(progData[1]) == "table" then
                            if progData[1].absolute ~= nil then
                                hasValue = true
                                value = progData[1].absolute
                                valueRaw = progData[1].absolute_value
                            end
                        end
                        
                        -- Also check top-level absolute
                        if not hasValue and progData.absolute ~= nil then
                            hasValue = true
                            value = progData.absolute
                            valueRaw = progData.absolute_value
                        end
                        
                        -- Get timing if present
                        if progData.fade then fade = progData.fade end
                        if progData.delay then delay = progData.delay end
                        
                        -- Check mask to see if value is active
                        if progData.mask_active_value and progData.mask_active_value > 0 then
                            hasValue = true
                        end
                        
                        if hasValue and value ~= nil then
                            local attrData = {
                                name = attrName or ch.SUBATTRIBUTE or ("UIChannel_" .. uiChIdx),
                                value = value
                            }
                            if valueRaw ~= nil then attrData.value_raw = valueRaw end
                            if fade ~= nil then attrData.fade = fade end
                            if delay ~= nil then attrData.delay = delay end
                            
                            -- Store as key-value for easier reading
                            fixtureData.attributes[attrData.name] = attrData.value
                            results.total_attributes = results.total_attributes + 1
                        end
                    end
                end
            end
        end
        
        -- Only add fixture if it has attributes in programmer
        if next(fixtureData.attributes) ~= nil then
            table.insert(results.fixtures, fixtureData)
            results.total_fixtures = results.total_fixtures + 1
        end
        
        idx = SelectionNext(idx)
    end
    
    if results.total_fixtures == 0 then
        results.warning = "Fixtures selected but no attribute values in programmer"
    end
    
    return serialize(results), nil
end

-- Handle cuecontents command (prefix "cuecontents:") - get contents of a cue
-- Format: cuecontents:cue_number [sequence_number] [part_number]
-- Example: cuecontents:1, cuecontents:1 1, cuecontents:1 1 0
local function handleCueContents(query)
    local parts = {}
    for part in query:gmatch("%S+") do
        table.insert(parts, part)
    end
    
    local cueNum = tonumber(parts[1])
    local seqNum = tonumber(parts[2]) or 1
    local partNum = tonumber(parts[3])
    
    if not cueNum then
        return nil, "Format: cuecontents:cue_number [sequence_number] [part_number]"
    end
    
    local results = {
        cue = cueNum,
        sequence = seqNum,
        fixtures = {}
    }
    
    -- Get the cue object - use dot notation: Sequence X.Cue Y
    local cueAddr = "Sequence " .. tostring(seqNum) .. ".Cue " .. tostring(cueNum)
    if partNum then
        cueAddr = cueAddr .. ".Part " .. tostring(partNum)
        results.part = partNum
    end
    
    local cueObj, err = getObjectByAddress(cueAddr)
    
    -- Try alternate format if dot notation fails
    if not cueObj then
        -- Try via DataPool and iterate sequence children (like handleChildren does)
        local success, dp = pcall(function() return DataPool() end)
        if success and dp then
            local seqSuccess, seq = pcall(function()
                return dp.Sequences[seqNum]
            end)
            if seqSuccess and seq then
                -- Iterate all cues using Count/Ptr (not seq.Cue!)
                local countSuccess, count = pcall(function() return seq:Count() end)
                if countSuccess and count then
                    for i = 1, count do
                        local ptrSuccess, c = pcall(function() return seq:Ptr(i) end)
                        if ptrSuccess and c then
                            local noSuccess, no = pcall(function() return c.no end)
                            if noSuccess and no == cueNum then
                                cueObj = c
                                break
                            end
                        end
                    end
                end
            end
        end
    end
    if not cueObj then
        return nil, "Cue not found: " .. cueAddr
    end
    
    -- Get cue properties
    local sn, n = pcall(function() return cueObj.name end)
    if sn and n then results.name = tostring(n) end
    
    -- Get timing properties using Get() method (more reliable)
    local timingProps = {
        {"CueInFade", "fade_in"},
        {"CueOutFade", "fade_out"},
        {"CueInDelay", "delay_in"},
        {"CueOutDelay", "delay_out"},
        {"Fade", "fade"},
        {"Delay", "delay"},
        {"TrigType", "trigger_type"},
        {"TrigTime", "trigger_time"},
        {"Duration", "duration"}
    }
    
    for _, propPair in ipairs(timingProps) do
        local propName, resultKey = propPair[1], propPair[2]
        local sp, pv = pcall(function() return cueObj:Get(propName) end)
        if sp and pv ~= nil and pv ~= "" then
            results[resultKey] = tostring(pv)
        end
    end
    
    -- Also try getAllProperties as fallback
    local props = getAllProperties(cueObj)
    if props then
        if not results.trigger_type and props.TrigType then results.trigger_type = props.TrigType end
    end
    
    -- Get cue parts info and timing from Part 0
    local scnt, partCount = pcall(function() return cueObj:Count() end)
    
    if scnt and partCount and partCount > 0 then
        results.has_parts = true
        results.part_count = partCount
        
        -- Get Part 0 for the main timing values (fade times are on Parts!)
        local sp0, part0 = pcall(function() return cueObj:Ptr(1) end)
        
        if sp0 and part0 then
            local partProps = getAllProperties(part0)
            if partProps then
                -- Get fade times from Part 0 (property names are UPPERCASE)
                -- Check for both number and non-"CueTiming" string values
                if partProps.CUEINFADE ~= nil then
                    if type(partProps.CUEINFADE) == "number" then
                        results.fade_in = partProps.CUEINFADE
                    elseif partProps.CUEINFADE ~= "CueTiming" then
                        results.fade_in = partProps.CUEINFADE
                    end
                end
                if partProps.CUEOUTFADE ~= nil then
                    if type(partProps.CUEOUTFADE) == "number" then
                        results.fade_out = partProps.CUEOUTFADE
                    elseif partProps.CUEOUTFADE ~= "CueTiming" then
                        results.fade_out = partProps.CUEOUTFADE
                    end
                end
                if partProps.CUEINDELAY ~= nil then
                    if type(partProps.CUEINDELAY) == "number" then
                        results.delay_in = partProps.CUEINDELAY
                    elseif partProps.CUEINDELAY ~= "CueTiming" then
                        results.delay_in = partProps.CUEINDELAY
                    end
                end
                if partProps.CUEOUTDELAY ~= nil then
                    if type(partProps.CUEOUTDELAY) == "number" then
                        results.delay_out = partProps.CUEOUTDELAY
                    elseif partProps.CUEOUTDELAY ~= "CueTiming" then
                        results.delay_out = partProps.CUEOUTDELAY
                    end
                end
                if partProps.DURATION then results.duration = partProps.DURATION end
                if partProps.SNAPDELAY then results.snap_delay = partProps.SNAPDELAY end
                if partProps.TRANSITION then results.transition = partProps.TRANSITION end
            end
        end
    end
    
    -- Collect all parts info
    local successChildren, children = pcall(function() return cueObj:Children() end)
    if successChildren and children then
        results.parts = {}
        for i, child in ipairs(children) do
            local partInfo = {}
            local scn, cn = pcall(function() return child.name end)
            if scn and cn then partInfo.name = tostring(cn) end
            
            local partProps = getAllProperties(child)
            if partProps then
                if partProps.PART ~= nil then partInfo.part = partProps.PART end
                if partProps.CUEINFADE and partProps.CUEINFADE ~= "CueTiming" then 
                    partInfo.fade_in = partProps.CUEINFADE 
                end
                if partProps.CUEOUTFADE and partProps.CUEOUTFADE ~= "CueTiming" then 
                    partInfo.fade_out = partProps.CUEOUTFADE 
                end
                if partProps.CUEINDELAY and partProps.CUEINDELAY ~= "CueTiming" then 
                    partInfo.delay_in = partProps.CUEINDELAY 
                end
                if partProps.DURATION then partInfo.duration = partProps.DURATION end
            end
            table.insert(results.parts, partInfo)
        end
    end
    
    -- Note: Getting actual fixture values from cues requires deep traversal
    -- of the cue data structure which varies by MA3 version
    results.note = "Use Track Sheet in MA3 to see detailed fixture values"
    
    return serialize(results), nil
end

-- Handle fixstatus command (prefix "fixstatus:") - get fixture output status
-- Format: fixstatus:fixture_id
-- Example: fixstatus:1
local function handleFixStatus(query)
    local fixId = tonumber(query)
    if not fixId then
        return nil, "Format: fixstatus:fixture_id (e.g., fixstatus:1)"
    end
    
    local results = {
        fixture_id = fixId,
        output_values = {}
    }
    
    -- Get fixture info
    local success1, fixtures = pcall(function()
        return ObjectList("Fixture " .. tostring(fixId))
    end)
    
    if not success1 or not fixtures or #fixtures == 0 then
        return nil, "Fixture " .. tostring(fixId) .. " not found"
    end
    
    local fixture = fixtures[1]
    results.name = fixture.name
    results.patch = fixture.patch
    
    -- Check if fixture is selected
    local isSelected = false
    local idx = SelectionFirst()
    while idx ~= nil do
        local sf = GetSubfixture(idx)
        if sf then
            local sfid, fid = pcall(function() return sf.fid end)
            if sfid and fid == fixId then
                isSelected = true
                break
            end
        end
        idx = SelectionNext(idx)
    end
    results.selected = isSelected
    
    -- Get the patch index for this fixture
    local subfixtureCount = GetSubfixtureCount()
    local patchIdx = nil
    
    for i = 0, subfixtureCount - 1 do
        local sf = GetSubfixture(i)
        if sf then
            local sfid = nil
            local s, fid = pcall(function() return sf.fid end)
            if s and fid then sfid = fid end
            if not sfid then
                local s2, no = pcall(function() return sf.no end)
                if s2 and no then sfid = no end
            end
            if sfid == fixId then
                patchIdx = i
                break
            end
        end
    end
    
    if patchIdx == nil then
        patchIdx = fixId - 1
    end
    results.patch_index = patchIdx
    
    -- Get parameter values via UI channels (not DMX values)
    results.in_programmer = false
    results.programmer_values = {}
    results.output_values = {}
    
    local successUi, uiChannels = pcall(function()
        return GetUIChannels(patchIdx, true)
    end)
    
    if successUi and uiChannels then
        for _, ch in ipairs(uiChannels) do
            if ch.INDEX then
                local uiChIdx = ch.INDEX - 1
                
                -- Get attribute name
                local attrName = ch.SUBATTRIBUTE or ("Attr_" .. uiChIdx)
                local sa, attr = pcall(function()
                    return GetAttributeByUIChannel(uiChIdx)
                end)
                if sa and attr then
                    local san, an = pcall(function() return attr.name end)
                    if san and an then attrName = tostring(an) end
                end
                
                -- Get programmer value for this UI channel
                local successProg, progData = pcall(function()
                    return GetProgPhaser(uiChIdx, false)
                end)
                
                if successProg and progData and type(progData) == "table" then
                    local hasValue = false
                    local value = nil
                    
                    -- Check step1 first (most common for static values)
                    if progData[1] and type(progData[1]) == "table" then
                        if progData[1].absolute ~= nil then
                            hasValue = true
                            value = progData[1].absolute
                        end
                    end
                    
                    -- Also check top-level absolute
                    if not hasValue and progData.absolute ~= nil then
                        hasValue = true
                        value = progData.absolute
                    end
                    
                    -- Check mask to see if value is active
                    if progData.mask_active_value and progData.mask_active_value > 0 then
                        hasValue = true
                    end
                    
                    if hasValue then
                        results.in_programmer = true
                        if value ~= nil then
                            results.programmer_values[attrName] = value
                        end
                    end
                end
                
                -- Get current output value via GetUIChannel
                local successUiCh, uiChData = pcall(function()
                    return GetUIChannel(patchIdx, uiChIdx)
                end)
                
                if successUiCh and uiChData and type(uiChData) == "table" then
                    if uiChData.value ~= nil then
                        results.output_values[attrName] = uiChData.value
                    elseif uiChData.absolute ~= nil then
                        results.output_values[attrName] = uiChData.absolute
                    end
                end
            end
        end
    end
    
    return serialize(results), nil
end

-- Handle seqoverview command (prefix "seqoverview:") - get sequence overview with all cues
-- Format: seqoverview:sequence_number
-- Example: seqoverview:1
local function handleSeqOverview(query)
    local seqNum = tonumber(query) or 1
    
    local results = {
        sequence = seqNum,
        cues = {}
    }
    
    -- Get the sequence via DataPool (more reliable)
    local seq = nil
    local success, dp = pcall(function() return DataPool() end)
    if success and dp then
        local seqSuccess, s = pcall(function() return dp.Sequences[seqNum] end)
        if seqSuccess and s then
            seq = s
        end
    end
    
    -- Fallback to getObjectByAddress
    if not seq then
        seq = getObjectByAddress("Sequence " .. tostring(seqNum))
    end
    
    if not seq then
        return nil, "Sequence " .. tostring(seqNum) .. " not found"
    end
    
    -- Get sequence name
    local sn, n = pcall(function() return seq.name end)
    if sn and n then results.name = tostring(n) end
    
    -- Get sequence properties
    local seqProps = getAllProperties(seq)
    if seqProps then
        if seqProps.Priority then results.priority = seqProps.Priority end
    end
    
    -- Check playback status
    local shp, hasPlayback = pcall(function() return seq:HasActivePlayback() end)
    if shp then results.is_playing = hasPlayback end
    
    -- Get current cue number if playing
    local sccp, currentCue = pcall(function() return seq:Get("CurrentCue") end)
    if sccp and currentCue then results.current_cue = tostring(currentCue) end
    
    -- Iterate cues directly using seq:Count() and seq:Ptr() 
    -- (like handleChildren does - this gives us ALL cues)
    local success, count = pcall(function() return seq:Count() end)
    if success and count and count > 0 then
        for i = 1, count do
            local sc, cue = pcall(function() return seq:Ptr(i) end)
            if sc and cue then
                local cueData = {}
                
                -- Get cue number
                local scno, cno = pcall(function() return cue.no end)
                if scno and cno then cueData.cue = cno end
                
                -- Get cue name
                local scn, cn = pcall(function() return cue.name end)
                if scn and cn and cn ~= "" then cueData.name = tostring(cn) end
                
                -- Get cue properties using Get()
                local timingProps = {
                    {"CueInFade", "fade_in"},
                    {"CueOutFade", "fade_out"},
                    {"Fade", "fade"},
                    {"TrigType", "trigger"},
                    {"TrigTime", "trigger_time"}
                }
                
                for _, propPair in ipairs(timingProps) do
                    local propName, resultKey = propPair[1], propPair[2]
                    local sp, pv = pcall(function() return cue:Get(propName) end)
                    if sp and pv ~= nil and pv ~= "" then
                        cueData[resultKey] = tostring(pv)
                    end
                end
                
                -- Check for cue parts
                local spc, partCount = pcall(function() return cue:Count() end)
                if spc and partCount and partCount > 0 then
                    cueData.has_parts = true
                    cueData.part_count = partCount
                end
                
                -- Only add if we got a cue number (skip internal objects)
                if cueData.cue then
                    table.insert(results.cues, cueData)
                end
            end
        end
    end
    
    -- Update cue_count based on actual cues found
    results.cue_count = #results.cues
    
    return serialize(results), nil
end


-- =============================================================================
-- SEQUENCE & EXECUTOR HANDLERS
-- =============================================================================

-- Handle listexec command (prefix "listexec:") - list executors with assigned objects
-- Format: listexec: or listexec:page_number
-- Example: listexec:1
local function handleListExec(query)
    local pageNum = tonumber(query) or 1
    
    local results = {
        page = pageNum,
        executors = {}
    }
    
    -- Get the page
    local page, err = getObjectByAddress("Page " .. tostring(pageNum))
    if not page then
        return nil, "Page " .. tostring(pageNum) .. " not found"
    end
    
    local success, count = pcall(function() return page:Count() end)
    if not success or not count then
        return nil, "Could not get executor count for page"
    end
    
    results.executor_count = count
    
    for i = 1, count do
        local sc, exec = pcall(function() return page:Ptr(i) end)
        if sc and exec then
            local execData = {}
            
            -- Get executor number
            local sno, no = pcall(function() return exec.no end)
            if sno and no then execData.no = no end
            
            -- Get executor name
            local sn, n = pcall(function() return exec.name end)
            if sn and n and n ~= "" then execData.name = tostring(n) end
            
            -- Get assigned object
            local sa, assigned = pcall(function() return exec:GetAssignedObj() end)
            if sa and assigned then
                local san, an = pcall(function() return assigned.name end)
                if san and an then execData.assigned_name = tostring(an) end
                local saa, aa = pcall(function() return assigned:Addr() end)
                if saa and aa then execData.assigned_addr = tostring(aa) end
                local sac, ac = pcall(function() return assigned:GetClass() end)
                if sac and ac then execData.assigned_class = tostring(ac) end
            end
            
            -- Check if executor has active playback
            local shp, hp = pcall(function() return exec:HasActivePlayback() end)
            if shp then execData.is_running = hp end
            
            -- Only include executors that have something assigned or have a name
            if execData.assigned_name or execData.name then
                table.insert(results.executors, execData)
            end
        end
    end
    
    return serialize(results), nil
end

-- Handle execfader command (prefix "execfader:") - set executor fader level
-- Format: execfader:page.executor value
-- Example: execfader:1.201 100
local function handleExecFader(query)
    local execAddr, value = query:match("^([%d%.]+)%s+(%d+)$")
    if not execAddr or not value then
        return nil, "Format: execfader:page.executor value (e.g., execfader:1.201 100)"
    end
    
    value = tonumber(value)
    
    -- Parse page.executor
    local pageNum, execNum = execAddr:match("^(%d+)%.(%d+)$")
    if not pageNum then
        -- Maybe just executor number, assume page 1
        pageNum = 1
        execNum = tonumber(execAddr)
    else
        pageNum = tonumber(pageNum)
        execNum = tonumber(execNum)
    end
    
    local results = {
        page = pageNum,
        executor = execNum,
        value = value
    }
    
    -- Get the executor object
    local exec, err = getObjectByAddress("Page " .. tostring(pageNum) .. "." .. tostring(execNum))
    if not exec then
        return nil, "Executor Page " .. tostring(pageNum) .. "." .. tostring(execNum) .. " not found"
    end
    
    -- Try to set fader using SetFader
    local success, setErr = pcall(function()
        exec:SetFader({value = value, faderEnabled = true})
    end)
    
    if success then
        results.status = "OK"
        results.method = "SetFader"
    else
        -- Fallback: try Cmd approach
        local cmdResult = Cmd("Executor " .. tostring(pageNum) .. "." .. tostring(execNum) .. " At " .. tostring(value))
        results.cmd_result = cmdResult
        
        if cmdResult == "OK" or cmdResult == "Ok" then
            results.status = "OK"
            results.method = "Cmd"
        else
            -- Try alternative syntax
            cmdResult = Cmd("Set Executor " .. tostring(pageNum) .. "." .. tostring(execNum) .. " Fader " .. tostring(value))
            results.cmd_result2 = cmdResult
            results.status = (cmdResult == "OK" or cmdResult == "Ok") and "OK" or "FAILED"
            results.method = "Set Cmd"
        end
    end
    
    return serialize(results), nil
end

-- Handle execgo command (prefix "execgo:") - trigger executor playback
-- Format: execgo:page.executor action
-- Actions: go, off, top, pause, toggle
-- Example: execgo:1.201 go
local function handleExecGo(query)
    local execAddr, action = query:match("^([%d%.]+)%s*(.*)$")
    if not execAddr then
        return nil, "Format: execgo:page.executor [action] (e.g., execgo:1.201 go)"
    end
    
    action = action:match("^%s*(.-)%s*$") or "go"  -- trim, default to go
    if action == "" then action = "go" end
    
    -- Parse page.executor
    local pageNum, execNum = execAddr:match("^(%d+)%.(%d+)$")
    if not pageNum then
        pageNum = 1
        execNum = tonumber(execAddr)
    else
        pageNum = tonumber(pageNum)
        execNum = tonumber(execNum)
    end
    
    local results = {
        page = pageNum,
        executor = execNum,
        action = action
    }
    
    -- Map action to MA3 command
    local cmdMap = {
        go = "Go+",
        ["go+"] = "Go+",
        ["go-"] = "Go-",
        back = "Go-",
        off = "Off",
        top = "Top",
        pause = "Pause",
        toggle = "Toggle",
        on = "On",
        flash = "Flash"
    }
    
    local ma3Cmd = cmdMap[action:lower()]
    if not ma3Cmd then
        return nil, "Unknown action: " .. action .. ". Use: go, off, top, pause, toggle, on, flash"
    end
    
    -- Try multiple command formats - MA3 executor syntax varies
    local cmdFormats = {
        ma3Cmd .. " Page " .. tostring(pageNum) .. "." .. tostring(execNum),
        ma3Cmd .. " Executor " .. tostring(execNum),  -- Uses current page
        ma3Cmd .. " Page " .. tostring(pageNum) .. " Executor " .. tostring(execNum)
    }
    
    local cmdResult = nil
    local cmdUsed = nil
    for _, cmdStr in ipairs(cmdFormats) do
        cmdResult = Cmd(cmdStr)
        cmdUsed = cmdStr
        -- Cmd() returns "OK" (uppercase) or nil on success
        if cmdResult == "OK" or cmdResult == "Ok" or cmdResult == nil then
            break
        end
    end
    
    results.command = cmdUsed
    results.result = cmdResult
    results.status = (cmdResult == "OK" or cmdResult == "Ok" or cmdResult == nil) and "OK" or "FAILED"
    
    return serialize(results), nil
end

-- Handle getcue command (prefix "getcue:") - get current cue position of a sequence
-- Format: getcue:sequence_number
-- Example: getcue:1
local function handleGetCue(query)
    local seqNum = tonumber(query)
    if not seqNum then
        -- Try to get selected sequence
        local selSeq = SelectedSequence()
        if selSeq then
            seqNum = selSeq.no or 1
        else
            seqNum = 1
        end
    end
    
    local results = {
        sequence = seqNum
    }
    
    -- Get the sequence
    local seq, err = getObjectByAddress("Sequence " .. tostring(seqNum))
    if not seq then
        return nil, "Sequence " .. tostring(seqNum) .. " not found"
    end
    
    -- Get sequence name
    local sn, n = pcall(function() return seq.name end)
    if sn and n then results.sequence_name = tostring(n) end
    
    -- Try to get current cue using various methods
    
    -- Method 1: Try CurrentCue property
    local scc, currentCue = pcall(function() return seq:Get("CurrentCue") end)
    if scc and currentCue then
        if type(currentCue) == "userdata" then
            local scn, cn = pcall(function() return currentCue.name end)
            if scn and cn then results.current_cue_name = tostring(cn) end
            local scno, cno = pcall(function() return currentCue.no end)
            if scno and cno then results.current_cue = cno end
        else
            results.current_cue = currentCue
        end
    end
    
    -- Method 2: Try Cue property
    local sc2, cue2 = pcall(function() return seq:Get("Cue") end)
    if sc2 and cue2 then
        results.cue_property = cue2
    end
    
    -- Method 3: Try CueA (for sequences with A/B crossfade)
    local sca, cueA = pcall(function() return seq:Get("CueA") end)
    if sca and cueA then
        if type(cueA) == "number" then
            results.cue_a = cueA
        elseif type(cueA) == "userdata" then
            local scan, can = pcall(function() return cueA.no end)
            if scan and can then results.cue_a = can end
        end
    end
    
    -- Method 4: Try CueB
    local scb, cueB = pcall(function() return seq:Get("CueB") end)
    if scb and cueB then
        if type(cueB) == "number" then
            results.cue_b = cueB
        elseif type(cueB) == "userdata" then
            local scbn, cbn = pcall(function() return cueB.no end)
            if scbn and cbn then results.cue_b = cbn end
        end
    end
    
    -- Method 5: Try to get playback status
    local shp, hasPlayback = pcall(function() return seq:HasActivePlayback() end)
    if shp then results.is_playing = hasPlayback end
    
    -- Method 6: Get cue count for context
    local cues, cerr = getObjectByAddress("Sequence " .. tostring(seqNum) .. ".Cue")
    if cues then
        local scc2, cueCount = pcall(function() return cues:Count() end)
        if scc2 and cueCount then results.cue_count = cueCount end
    end
    
    return serialize(results), nil
end

-- Handle seqstatus command (prefix "seqstatus:") - get detailed sequence status
-- Format: seqstatus:sequence_number
-- Example: seqstatus:1
local function handleSeqStatus(query)
    local seqNum = tonumber(query) or 1
    
    local results = {
        sequence = seqNum
    }
    
    -- Get the sequence
    local seq, err = getObjectByAddress("Sequence " .. tostring(seqNum))
    if not seq then
        return nil, "Sequence " .. tostring(seqNum) .. " not found"
    end
    
    -- Get sequence name
    local sn, n = pcall(function() return seq.name end)
    if sn and n then results.name = tostring(n) end
    
    -- Get various properties
    local props = {"CueFade", "CueOutFade", "CueDelay", "CueOutDelay", "Priority", "Master", "Speed", "Rate"}
    for _, prop in ipairs(props) do
        local sp, pv = pcall(function() return seq:Get(prop) end)
        if sp and pv ~= nil then
            results[prop:lower()] = pv
        end
    end
    
    -- Check playback status
    local shp, hasPlayback = pcall(function() return seq:HasActivePlayback() end)
    if shp then results.is_playing = hasPlayback end
    
    -- Get fader value if available
    local sf, fader = pcall(function() return seq:GetFader({token = "FaderMaster"}) end)
    if sf and fader then results.fader_master = fader end
    
    return serialize(results), nil
end


-- =============================================================================
-- COMMAND DISPATCHER
-- =============================================================================

local function executeCommand(command)
    if not command or command == "" then
        return nil, "Empty command"
    end
    
    -- Direct MA3 command (prefix with "cmd:")
    if command:sub(1, 4) == "cmd:" then
        local cmdStr = command:sub(5)
        local success, result = pcall(function()
            return Cmd(cmdStr)
        end)
        if success then
            if result == nil then
                return "OK", nil
            elseif type(result) == "table" then
                return serialize(result), nil
            else
                return tostring(result), nil
            end
        else
            return nil, tostring(result)
        end
    end
    
    -- Query object by address (prefix with "?")
    if command:sub(1, 1) == "?" then
        return handleQuery(command:sub(2))
    end
    
    -- Get property (prefix with "get:")
    if command:sub(1, 4) == "get:" then
        return handleGet(command:sub(5))
    end
    
    -- Get all properties (prefix with "props:")
    if command:sub(1, 6) == "props:" then
        return handleProps(command:sub(7))
    end
    
    -- List children (prefix with "children:")
    if command:sub(1, 9) == "children:" then
        return handleChildren(command:sub(10))
    end
    
    -- Get fixture attribute (prefix with "getattr:")
    if command:sub(1, 8) == "getattr:" then
        return handleGetAttr(command:sub(9))
    end
    
    -- List fixture attributes (prefix with "listattr:")
    if command:sub(1, 9) == "listattr:" then
        return handleListAttr(command:sub(10))
    end
    
    -- List all patched fixtures (prefix with "listfix:")
    if command:sub(1, 8) == "listfix:" then
        return handleListFix(command:sub(9))
    end
    
    -- Also allow just "listfix" without colon
    if command == "listfix" then
        return handleListFix("")
    end
    
    -- Get DMX value (prefix with "getdmx:")
    if command:sub(1, 7) == "getdmx:" then
        return handleGetDMX(command:sub(8))
    end
    
    -- Get DMX universe (prefix with "dmxuni:")
    if command:sub(1, 7) == "dmxuni:" then
        return handleDMXUniverse(command:sub(8))
    end
    
    -- List programmer contents (prefix with "listprog:")
    if command:sub(1, 9) == "listprog:" then
        return handleListProg(command:sub(10))
    end
    
    -- Also allow just "listprog" without colon
    if command == "listprog" then
        return handleListProg("")
    end
    
    -- Get programmer values (prefix with "getprog:")
    if command:sub(1, 8) == "getprog:" then
        return handleGetProg(command:sub(9))
    end
    
    -- Get current selection (prefix with "getselection:")
    if command:sub(1, 13) == "getselection:" then
        return handleGetSelection(command:sub(14))
    end
    if command == "getselection" then
        return handleGetSelection("")
    end
    
    -- Select fixtures (prefix with "select:")
    if command:sub(1, 7) == "select:" then
        return handleSelect(command:sub(8))
    end
    
    -- Set attribute on current selection (prefix with "setattr:")
    if command:sub(1, 8) == "setattr:" then
        return handleSetAttr(command:sub(9))
    end
    
    -- Set color on current selection (prefix with "setcolor:")
    if command:sub(1, 9) == "setcolor:" then
        return handleSetColor(command:sub(10))
    end
    
    -- List groups (prefix with "listgroups:")
    if command:sub(1, 11) == "listgroups:" then
        return handleListGroups(command:sub(12))
    end
    
    -- Also allow just "listgroups" without colon
    if command == "listgroups" then
        return handleListGroups("")
    end
    
    -- Detailed programmer contents (prefix with "progdetail:")
    if command == "progdetail" or command:sub(1, 11) == "progdetail:" then
        return handleProgDetail(command:sub(12))
    end
    
    -- Cue contents (prefix with "cuecontents:")
    if command:sub(1, 12) == "cuecontents:" then
        return handleCueContents(command:sub(13))
    end
    
    -- Fixture status (prefix with "fixstatus:")
    if command:sub(1, 10) == "fixstatus:" then
        return handleFixStatus(command:sub(11))
    end
    
    -- Sequence overview (prefix with "seqoverview:")
    if command:sub(1, 12) == "seqoverview:" then
        return handleSeqOverview(command:sub(13))
    end
    
    -- Also allow just "seqoverview" without colon (defaults to sequence 1)
    if command == "seqoverview" then
        return handleSeqOverview("1")
    end
    
    -- List executors (prefix with "listexec:")
    if command:sub(1, 9) == "listexec:" then
        return handleListExec(command:sub(10))
    end
    
    -- Also allow just "listexec" without colon
    if command == "listexec" then
        return handleListExec("")
    end
    
    -- Executor fader control (prefix with "execfader:")
    if command:sub(1, 10) == "execfader:" then
        return handleExecFader(command:sub(11))
    end
    
    -- Executor playback control (prefix with "execgo:")
    if command:sub(1, 7) == "execgo:" then
        return handleExecGo(command:sub(8))
    end
    
    -- Get current cue (prefix with "getcue:")
    if command:sub(1, 7) == "getcue:" then
        return handleGetCue(command:sub(8))
    end
    
    -- Also allow just "getcue" without colon (uses selected sequence)
    if command == "getcue" then
        return handleGetCue("")
    end
    
    -- Get sequence status (prefix with "seqstatus:")
    if command:sub(1, 10) == "seqstatus:" then
        return handleSeqStatus(command:sub(11))
    end
    
    -- Regular MA3 command via Cmd()
    local success, result = pcall(function()
        return Cmd(command)
    end)
    if success then
        if result == nil then
            return "OK", nil
        elseif type(result) == "table" then
            return serialize(result), nil
        else
            return tostring(result), nil
        end
    else
        return nil, tostring(result)
    end
end

local function poll()
    local success, err = pcall(function()
        local raw = readFile(COMMAND_FILE)
        if not raw then 
            return 
        end
        
        local requestId, command = parseCommand(raw)
        if not command or command == "" then 
            return 
        end
        if requestId and requestId == lastRequestId then 
            return 
        end
        
        if requestId then
            lastRequestId = requestId
        end
        
        log("Executing: " .. command)
        
        local result, execErr = executeCommand(command)
        local response
        if execErr then
            response = "ERR:" .. execErr
        else
            response = result or "OK"
        end
        
        if requestId then
            response = requestId .. ":" .. response
        end
        
        writeFile(RESPONSE_FILE, response)
        log("Response: " .. response)
    end)
    
    if not success then
        log("Poll error: " .. tostring(err))
        -- Try to write error response
        pcall(function()
            writeFile(RESPONSE_FILE, "ERR:Plugin error: " .. tostring(err))
        end)
    end
end


-- =============================================================================
-- COLD-START AUTOLOAD (WS1 / onPC reboot without Menu -> Plugins)
-- =============================================================================
-- MA3 2.3.2 has no UserPlugin Autostart. Official cold-start:
--   RUNPLUGIN="MCP Server.xml"-1
-- Operator or start-onpc-with-mcp.ps1 writes "go" to mcp_autoload.txt before launch.
-- This one-shot hook acknowledges cold start; RUNPLUGIN already loaded this component.

local function tryAutoload()
    local raw = readFile(AUTOLOAD_FILE)
    if not raw or raw == "" then
        return
    end

    local token = raw:match("^%s*(%S+)")
    if token ~= "go" then
        return
    end

    writeFile(AUTOLOAD_FILE, "done\n")
    log("autoload go -> MCP plugin running (cold start via RUNPLUGIN)")
end

-- =============================================================================
-- MAIN PLUGIN ENTRY POINT
-- =============================================================================

local function Main(display_handle, argument)
    tryAutoload()

    Printf("===================================")
    Printf("MCP Shared File Plugin started")
    Printf("Command file: " .. COMMAND_FILE)
    Printf("Response file: " .. RESPONSE_FILE)
    Printf("===================================")
    
    -- Test file access
    local testRead = readFile(COMMAND_FILE)
    if testRead then
        Printf("MCP: Command file readable")
    else
        Printf("MCP: WARNING - Cannot read command file!")
    end
    
    local testWrite = writeFile(RESPONSE_FILE, "")
    if testWrite then
        Printf("MCP: Response file writable")
    else
        Printf("MCP: WARNING - Cannot write response file!")
    end
    
    while true do
        poll()
        coroutine.yield(0.1)
    end
end

local function Cleanup()
    Printf("MCP Shared File Plugin stopped")
end

return Main, Cleanup
