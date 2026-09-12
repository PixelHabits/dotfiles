-- highlight yank
vim.api.nvim_create_autocmd('TextYankPost', {
	group = vim.api.nvim_create_augroup('highlight_yank', { clear = true }),
	pattern = '*',
	desc = 'highlight selection on yank',
	callback = function()
		local highlight = vim.hl.hl_op or vim.hl.on_yank
		highlight({ timeout = 200, on_visual = true })
	end,
})

-- syntax highlighting for dotenv files
vim.api.nvim_create_autocmd('BufRead', {
	group = vim.api.nvim_create_augroup('dotenv_ft', { clear = true }),
	pattern = { '.env', '.env.*' },
	callback = function()
		vim.bo.filetype = 'dosini'
	end,
})
