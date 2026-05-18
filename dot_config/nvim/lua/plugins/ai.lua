vim.pack.add({
	{ src = 'https://github.com/folke/sidekick.nvim' },
})

require('sidekick').setup({
	cli = {
		mux = {
			enabled = vim.env.ZELLIJ ~= nil or vim.env.TMUX ~= nil,
		},
		picker = 'fzf-lua',
	},
})

vim.keymap.set('n', '<Tab>', function()
	return require('sidekick').nes_jump_or_apply() and '' or '<Tab>'
end, { expr = true, desc = 'Sidekick next edit suggestion' })

vim.keymap.set({ 'n', 't', 'i', 'x' }, '<C-.>', function()
	require('sidekick.cli').focus()
end, { desc = 'Sidekick focus' })

vim.keymap.set('n', '<leader>aa', function()
	require('sidekick.cli').toggle()
end, { desc = 'Sidekick toggle CLI' })

vim.keymap.set('n', '<leader>as', function()
	require('sidekick.cli').select({ filter = { installed = true } })
end, { desc = 'Sidekick select CLI' })

vim.keymap.set('n', '<leader>ad', function()
	require('sidekick.cli').close()
end, { desc = 'Sidekick detach CLI' })

vim.keymap.set({ 'n', 'x' }, '<leader>at', function()
	require('sidekick.cli').send({ msg = '{this}' })
end, { desc = 'Sidekick send this' })

vim.keymap.set('n', '<leader>af', function()
	require('sidekick.cli').send({ msg = '{file}' })
end, { desc = 'Sidekick send file' })

vim.keymap.set('x', '<leader>av', function()
	require('sidekick.cli').send({ msg = '{selection}' })
end, { desc = 'Sidekick send selection' })

vim.keymap.set({ 'n', 'x' }, '<leader>ap', function()
	require('sidekick.cli').prompt()
end, { desc = 'Sidekick prompt' })
