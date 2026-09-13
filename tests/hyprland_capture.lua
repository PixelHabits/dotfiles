-- Capture declarations only. No compositor calls or external commands run.
local calls = { binds = {}, monitors = {}, rules = {}, layers = {}, config = {}, curves = {}, animations = {}, startup = {}, env = {} }
local callbacks = {}
local function dispatcher(path)
    return setmetatable({}, {
        __index = function(_, key) return dispatcher(path .. "." .. key) end,
        __call = function(_, ...) return { name = path, args = { ... } } end,
    })
end
hl = {
    dsp = dispatcher("hl.dsp"),
    bind = function(keys, action, flags)
        if type(action) == "function" then callbacks[keys] = action; action = { callback = true } end
        table.insert(calls.binds, { keys = keys, action = action, flags = flags or {} })
    end,
    monitor = function(value) table.insert(calls.monitors, value) end,
    window_rule = function(value) table.insert(calls.rules, value) end,
    layer_rule = function(value) table.insert(calls.layers, value) end,
    config = function(value) table.insert(calls.config, value) end,
    curve = function(name, value) calls.curves[name] = value end,
    animation = function(value) table.insert(calls.animations, value) end,
    on = function(event, callback) assert(event == "hyprland.start"); callback() end,
    exec_cmd = function(command) table.insert(calls.startup, command) end,
    env = function(name, value) calls.env[name] = value end,
    gesture = function(value) calls.gesture = value end,
    device = function(value) calls.device = value end,
}
package.path = arg[1] .. "/?.lua;" .. package.path
dofile(arg[1] .. "/hyprland.lua")

-- Exercise registered callbacks only against this fake API, after capturing startup monitors.
local configured_monitors = calls.monitors
calls.monitors = {}
for _, callback in pairs(callbacks) do callback() end
calls.callback_monitors = calls.monitors
calls.monitors = configured_monitors

local function json(value)
    local kind = type(value)
    if kind == "string" then
        return '"' .. value:gsub('[%z\1-\31\\"]', function(c)
            return ({ ['"'] = '\\"', ['\\'] = '\\\\' })[c] or string.format('\\u%04x', c:byte())
        end) .. '"'
    elseif kind == "boolean" or kind == "number" then
        return tostring(value)
    elseif kind == "table" then
        local result = {}
        if #value > 0 then
            for _, item in ipairs(value) do table.insert(result, json(item)) end
            return '[' .. table.concat(result, ',') .. ']'
        end
        for key, item in pairs(value) do table.insert(result, json(key) .. ':' .. json(item)) end
        return '{' .. table.concat(result, ',') .. '}'
    end
    error("unsupported JSON type: " .. kind)
end
print(json(calls))
