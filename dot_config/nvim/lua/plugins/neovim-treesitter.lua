vim.api.nvim_create_autocmd('PackChanged', {
	callback = function(ctx)
		local name, kind = ctx.data.spec.name, ctx.data.kind
		if name == 'nvim-treesitter' and kind == 'update' then
			if not ctx.data.active then
				vim.cmd.packadd('nvim-treesitter')
			end
			vim.cmd('TSUpdate')
		end
	end,
})

vim.pack.add({
	{ src = 'https://github.com/neovim-treesitter/treesitter-parser-registry' },
	{ src = 'https://github.com/neovim-treesitter/nvim-treesitter', version = 'main' },
	{ src = 'https://github.com/nvim-treesitter/nvim-treesitter-textobjects', version = 'main' },
})

local ts_langs = {
	'angular',
	'asm',
	'bash',
	'c',
	'c_sharp',
	'cmake',
	'comment',
	'cpp',
	'css',
	'csv',
	'desktop',
	'diff',
	'dockerfile',
	'dtd',
	'ecma',
	'editorconfig',
	'git_config',
	'git_rebase',
	'gitattributes',
	'gitcommit',
	'gitignore',
	'glimmer',
	'go',
	'gomod',
	'gosum',
	'gowork',
	'gpg',
	'graphql',
	'hcl',
	'html',
	'html_tags',
	'http',
	'hyprlang',
	'java',
	'javascript',
	'jsdoc',
	'json',
	'json5',
	'jsx',
	'latex',
	'lua',
	'luadoc',
	'luap',
	'make',
	'markdown',
	'markdown_inline',
	'matlab',
	'mermaid',
	'printf',
	'prisma',
	'python',
	'query',
	'regex',
	'requirements',
	'rust',
	'scss',
	'sql',
	'terraform',
	'toml',
	'tsv',
	'tsx',
	'typescript',
	'vim',
	'vimdoc',
	'vue',
	'xml',
	'yaml',
	'zig',
	'zsh',
}

require('nvim-treesitter').install(ts_langs)

vim.api.nvim_create_autocmd('FileType', {
	callback = function()
		local ok = pcall(vim.treesitter.start)
		if not ok then
			return
		end

		vim.wo.foldexpr = 'v:lua.vim.treesitter.foldexpr()'
		vim.wo.foldmethod = 'expr'
		vim.bo.indentexpr = "v:lua.require'nvim-treesitter'.indentexpr()"
	end,
})
