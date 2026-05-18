vim.pack.add({
	{ src = 'https://github.com/projekt0n/github-nvim-theme' },
})

require('github-theme').setup({
	options = {
		transparent = true,
	},
})
vim.cmd('colorscheme github_dark_default')
