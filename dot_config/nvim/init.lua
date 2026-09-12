if vim.fn.has('nvim-0.12') == 0 then
	vim.notify('This configuration requires Neovim 0.12 or later.', vim.log.levels.ERROR)
	return
end

vim.loader.enable()
require('config')
require('plugins')
