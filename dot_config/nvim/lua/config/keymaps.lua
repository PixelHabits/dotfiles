-- Inlay Hints
vim.keymap.set('n', '<leader>h', function()
	vim.lsp.inlay_hint.enable(not vim.lsp.inlay_hint.is_enabled())
	vim.notify(vim.lsp.inlay_hint.is_enabled() and 'Inlay Hints Enabled' or 'Inlay Hints Disabled')
end)

-- Notify when copying to the system clipboard
vim.keymap.set('v', '<D-c>', function()
	vim.notify('Copied to system clipboard', vim.log.levels.INFO)
	vim.cmd('normal! "+y')
end)

-- Notify when pasting from the system clipboard
vim.keymap.set('n', '<D-v>', function()
	vim.notify('Pasted from system clipboard', vim.log.levels.INFO)
	vim.cmd('normal! "+p')
end)

-- Clear highlights on search when pressing <Esc> in normal mode
--  See `:help hlsearch`
vim.keymap.set('n', '<Esc>', '<cmd>nohlsearch<CR>')
