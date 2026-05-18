vim.pack.add({
	{ src = 'https://github.com/j-hui/fidget.nvim' },
	{ src = 'https://github.com/nvim-lualine/lualine.nvim' },
	{ src = 'https://github.com/nvim-mini/mini.nvim' },
	{ src = 'https://github.com/folke/which-key.nvim' },
})

-- require('fidget').setup({})
require('which-key').setup()

require('lualine').setup({
	options = {
		component_separators = '',
	},
	sections = {
		lualine_a = { 'mode' },
		lualine_b = { 'branch', 'diff' },
		lualine_c = {
			{ 'filename', path = 1 },
			{
				function()
					return ' '
				end,
				color = function()
					local status = require('sidekick.status').get()
					if status then
						return status.kind == 'Error' and 'DiagnosticError' or status.busy and 'DiagnosticWarn' or 'Special'
					end
				end,
				cond = function()
					return require('sidekick.status').get() ~= nil
				end,
			},
		},
		lualine_x = {
			{
				function()
					local status = require('sidekick.status').cli()
					return ' ' .. (#status > 1 and #status or '')
				end,
				cond = function()
					return #require('sidekick.status').cli() > 0
				end,
				color = function()
					return 'Special'
				end,
			},
			'lsp_status',
		},
		lualine_y = { 'filetype' },
		lualine_z = {
			{
				'diagnostics',
				sources = { 'nvim_workspace_diagnostic' },
			},
		},
	},
	extensions = { 'quickfix', 'oil', 'fugitive', 'mason' },
})

-- enhanced, a and i keybinds
require('mini.ai').setup()

-- auto pairs
require('mini.pairs').setup()

-- access to surround keymaps sa,sd,sc etc
require('mini.surround').setup()

-- icons, replace nvim_web_devicons
require('mini.icons').setup()
MiniIcons.mock_nvim_web_devicons()

-- better jump capabilities
require('mini.jump').setup()

-- override vim.notify and show lsp info
require('mini.notify').setup({
	lsp_progress = {
		enable = false,
	},
	content = {
		format = function(notif)
			return notif.msg
		end,
	},
	window = {
		config = function()
			local has_tabline = vim.o.showtabline == 2 or (vim.o.showtabline == 1 and #vim.api.nvim_list_tabpages() > 1)

			return {
				border = 'rounded',
				col = vim.o.columns,
				row = has_tabline and 1 or 0,
				anchor = 'NE',
				title = '',
			}
		end,
	},
})

vim.api.nvim_set_hl(0, 'MiniNotifyBorder', { link = 'Pmenu' })

local orig = MiniNotify.make_notify()
local str_to_level = { trace = 0, debug = 1, info = 2, warn = 3, error = 4, off = 5 }

vim.notify = function(msg, level, opts)
	if type(level) == 'string' then
		level = str_to_level[level:lower()] or vim.log.levels.INFO
	end
	return orig(msg, level, opts)
end
