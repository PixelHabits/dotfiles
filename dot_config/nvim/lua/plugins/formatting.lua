vim.pack.add({
	{ src = 'https://github.com/stevearc/conform.nvim' },
	{ src = 'https://github.com/windwp/nvim-ts-autotag' },
})

require('conform').setup({
	format_on_save = function(bufnr)
		if vim.g.disable_autoformat or vim.b[bufnr].disable_autoformat then
			return
		end
		return { timeout_ms = 8000, lsp_format = 'fallback' }
	end,
	formatters_by_ft = {
		-- Biome supported languages
		css = { 'biome-check' },
		graphql = { 'biome-check' },
		gritql = { 'biome' },
		html = { 'biome-check', 'prettierd', stop_after_first = true },
		javascript = { 'biome-check' },
		javascriptreact = { 'biome-check' },
		json = { 'biome-check' },
		jsonc = { 'biome-check' },
		typescript = { 'biome-check' },
		typescriptreact = { 'biome-check' },

		-- Prettier-only languages
		angular = { 'prettierd' },
		handlebars = { 'prettierd' },
		less = { 'prettierd' },
		markdown = { 'prettierd' },
		['markdown.mdx'] = { 'prettierd' },
		scss = { 'prettierd' },
		vue = { 'prettierd' },
		yaml = { 'prettierd' },

		-- Other languages
		bash = { 'shfmt' },
		c = { 'clang-format' },
		cpp = { 'clang-format' },
		dockerfile = { 'dockerfmt' },
		go = { 'goimports', 'gofmt' },
		java = { 'google-java-format' },
		lua = { 'stylua' },
		python = { 'ruff_organize_imports', 'ruff_format' },
		rust = { 'rustfmt' },
		sh = { 'shfmt' },
		sql = { 'sql_formatter' },
		terraform = { 'terraform_fmt' },
		['terraform-vars'] = { 'terraform_fmt' },
		toml = { 'taplo' },
		xml = { 'xmllint' },

		-- Global helpers ran on all files
		['*'] = { 'injected', 'codespell' },

		-- Fallback cleanup for unconfigured filetypes
		['_'] = { 'trim_whitespace' },
	},
	formatters = {
		stylua = {
			prepend_args = { '--quote-style', 'AutoPreferSingle' },
		},
		sql_formatter = {
			prepend_args = { '--language', 'postgresql' },
		},
	},
})

vim.api.nvim_create_user_command('FormatDisable', function(args)
	if args.bang then
		vim.g.disable_autoformat = true
	else
		vim.b.disable_autoformat = true
	end
end, {
	desc = 'Disable autoformat-on-save for current buffer; use ! for global',
	bang = true,
})

vim.api.nvim_create_user_command('FormatEnable', function()
	vim.b.disable_autoformat = false
	vim.g.disable_autoformat = false
end, {
	desc = 'Re-enable autoformat-on-save',
})

require('nvim-ts-autotag').setup()
