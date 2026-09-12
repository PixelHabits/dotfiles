-- Run with: nvim --headless -u NONE -i NONE -l tests/nvim.lua
local root = vim.fn.getcwd()
local real_vim = vim
for _, method in ipairs({ 'hl_op', 'on_yank' }) do
  local callbacks, called = {}, false
  _G.vim = {
    api = {
      nvim_create_augroup = function() return 1 end,
      nvim_create_autocmd = function(event, opts) callbacks[event] = opts.callback end,
    },
    hl = { [method] = function(opts)
      assert(opts.timeout == 200 and opts.on_visual == true)
      called = true
    end },
    bo = {},
  }
  dofile(root .. '/dot_config/nvim/lua/config/autocmds.lua')
  callbacks.TextYankPost()
  assert(called, method)
end
_G.vim = real_vim
assert(dofile(root .. '/dot_config/nvim/lsp/gopls.lua').settings.gopls.env == nil)
local read = table.concat(vim.fn.readfile(root .. '/dot_config/nvim/lua/plugins/lsp.lua'), '\n')
assert(not read:find("copilot%-language%-server"))
-- Run the real yank callback without loading plugins or starting language servers.
dofile(root .. '/dot_config/nvim/lua/config/autocmds.lua')
vim.api.nvim_buf_set_lines(0, 0, -1, false, { 'hello' })
vim.cmd('normal! yy')
print('PASS: current/previous highlight APIs, real yank, and no forced Go experiment or Copilot install')
