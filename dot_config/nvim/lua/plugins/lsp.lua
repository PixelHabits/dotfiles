vim.pack.add({
	{ src = 'https://github.com/neovim/nvim-lspconfig.git' },
	{ src = 'https://github.com/mason-org/mason.nvim.git' },
	{ src = 'https://github.com/mason-org/mason-lspconfig.nvim' },
	{ src = 'https://github.com/WhoIsSethDaniel/mason-tool-installer.nvim' },
})

require('mason').setup()
require('mason-lspconfig').setup()
require('mason-tool-installer').setup({
	ensure_installed = {
		-- LSP Servers
		'ansiblels',
		'basedpyright',
		'bashls',
		'clangd',
		-- 'copilot-language-server',
		'cssls',
		'docker_compose_language_service',
		'dockerls',
		'gh_actions_ls',
		'gopls',
		'html',
		'jdtls',
		'jsonls',
		'lua_ls',
		'postgres_lsp',
		'tailwindcss',
		'terraformls',
		'tsgo',
		'yamlls',

		-- Formatters/Tools
		'ansible-lint',
		'biome',
		'clang-format',
		'codespell',
		-- 'dockerfmt',
		'goimports',
		'google-java-format',
		'prettierd',
		'ruff',
		'shfmt',
		'sql-formatter',
		'stylua',
		'taplo',
		'terraform',
	},
	run_on_start = true,
	auto_update = false,
	debounce_hours = 24,
})

-- LspAttach keymaps
vim.api.nvim_create_autocmd(
	'LspAttach',
	{ --  Use LspAttach autocommand to only map the following keys after the language server attaches to the current buffer
		group = vim.api.nvim_create_augroup('UserLspConfig', {}),
		callback = function(ev)
			local client = vim.lsp.get_client_by_id(ev.data.client_id)

			vim.bo[ev.buf].omnifunc = 'v:lua.vim.lsp.omnifunc' -- Enable completion triggered by <c-x><c-o>

			local opts = function(desc)
				return { buffer = ev.buf, silent = true, desc = desc }
			end
			vim.keymap.set('n', 'gd', vim.lsp.buf.definition, opts('Go to definition'))
			vim.keymap.set('n', '<leader><space>', vim.lsp.buf.hover, opts('Hover documentation'))
			vim.keymap.set('n', 'gi', vim.lsp.buf.implementation, opts('Go to implementation'))
			vim.keymap.set('n', '<leader>D', vim.lsp.buf.type_definition, opts('Go to type definition'))
			vim.keymap.set('n', '<leader>rn', vim.lsp.buf.rename, opts('Rename symbol'))
			vim.keymap.set('n', 'gr', vim.lsp.buf.references, opts('Find references'))

			vim.keymap.set({ 'n', 'v' }, '<leader>ca', function()
				require('tiny-code-action').code_action()
			end, opts('Code action'))
			vim.keymap.set('n', '<leader>f', vim.lsp.buf.format, opts('Format buffer'))

			vim.keymap.set('n', '<leader>d', function()
				vim.diagnostic.open_float({
					border = 'rounded',
				})
			end, opts('Show diagnostics float'))

			if client and client:supports_method(vim.lsp.protocol.Methods.textDocument_inlineCompletion, ev.buf) then
				vim.lsp.inline_completion.enable(true, { bufnr = ev.buf })
				vim.keymap.set('i', '<C-f>', vim.lsp.inline_completion.get, opts('Accept inline completion'))
				vim.keymap.set('i', '<C-g>', vim.lsp.inline_completion.select, opts('Next inline completion'))
			end
		end,
	}
)

-- mason-lspconfig only auto-enables servers installed by Mason; use PATH rust-analyzer.
vim.lsp.enable('rust_analyzer')
