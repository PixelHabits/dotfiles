vim.pack.add({
	{ src = 'https://github.com/L3MON4D3/LuaSnip' },
	{ src = 'https://github.com/Saghen/blink.lib' },
	{ src = 'https://github.com/Saghen/blink.cmp' },
	{ src = 'https://github.com/rafamadriz/friendly-snippets' },
})

require('luasnip.loaders.from_vscode').lazy_load()

local cmp = require('blink.cmp')
cmp.build():wait(60000)

cmp.setup({
	snippets = { preset = 'luasnip' },
	keymap = {
		preset = 'default',
		['<Tab>'] = {
			'snippet_forward',
			'accept',
			function()
				local ok, sidekick = pcall(require, 'sidekick')
				return ok and sidekick.nes_jump_or_apply()
			end,
			function()
				return vim.lsp.inline_completion.get()
			end,
			'fallback',
		},
		['<CR>'] = { 'accept', 'fallback' },
		['<S-Tab>'] = { 'show' },
		['<S-j>'] = { 'select_next', 'fallback' },
		['<S-k>'] = { 'select_prev', 'fallback' },
	},
	completion = {
		list = {
			selection = {
				preselect = false,
				auto_insert = false,
			},
		},
		menu = {
			scrollbar = false,
			auto_show = true,
			draw = {
				treesitter = { 'lsp' },
				columns = { { 'kind_icon', 'label', 'label_description', gap = 1 }, { 'kind' } },
			},
		},
		documentation = { auto_show = true },
	},
	signature = { enabled = true },
	fuzzy = { implementation = 'rust' },
	sources = {
		default = {
			'lsp',
			'path',
			'snippets',
			'buffer',
		},
		per_filetype = {
			sql = { 'lsp', 'snippets', 'buffer' },
		},
		providers = {
			lsp = {
				score_offset = 90,
			},
		},
	},
})
