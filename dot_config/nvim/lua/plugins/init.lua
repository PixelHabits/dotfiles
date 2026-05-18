vim.pack.add({
	{ src = 'https://github.com/wakatime/vim-wakatime' },
	{ src = 'https://github.com/ibhagwan/fzf-lua' },
})

require('plugins.colorscheme')
require('plugins.completions')
require('plugins.file-explorer')
require('plugins.formatting')
require('plugins.git')
require('plugins.lsp')
require('plugins.ai')
require('plugins.navigation')
require('plugins.neovim-treesitter')
require('plugins.qol')

require('fzf-lua').setup()
