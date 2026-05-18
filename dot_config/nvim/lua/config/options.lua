vim.g.mapleader = ' ' -- space leader key

vim.opt.updatetime = 200 -- save swap file with 200ms debouncing
vim.opt.undofile = true -- persistent undo history
vim.opt.number = true -- enable line numbers
vim.opt.relativenumber = true -- enable relative line numbers

vim.opt.completeopt = 'menu,menuone,noselect,preview' -- omnicomplete options for popup menu
vim.opt.pumheight = 10 -- max height of completion menu
vim.opt.winborder = 'rounded' -- rounded border
vim.o.showmode = false -- disable showing mode below statusline

vim.opt.cursorline = true -- enable cursor line
vim.opt.signcolumn = 'yes' -- always show sign column
vim.opt.ignorecase = true -- case-insensitive search
vim.opt.smartcase = true -- until search pattern contains upper case characters

vim.opt.tabstop = 2 -- how many spaces tab inserts
vim.opt.softtabstop = 2 -- how many spaces tab inserts
vim.opt.shiftwidth = 2 -- controls number of spaces when using >> or << commands
vim.opt.smartindent = true -- indenting correctly after {
vim.opt.scrolloff = 8 -- always keep 8 lines above/below cursor unless at start/end of file

vim.opt.splitbelow = true -- better splitting
vim.opt.splitright = true -- better splitting

vim.o.laststatus = 3 -- Global Statusline

-- vim.opt.wrap = false -- disable wrap
vim.opt.foldlevel = 99

vim.diagnostic.config({ virtual_text = true }) --inline diagnostics

--  See `:help 'list'`
--  and `:help 'listchars'`
vim.opt.list = true
vim.opt.listchars = { space = '·', eol = '↵', tab = '→ ', trail = '×', nbsp = '␣' }
-- vim.opt.listchars = { tab = "» ", trail = "·", nbsp = "␣" }

-- Column marker
vim.opt.colorcolumn = '80' -- Highlight column 80 (useful for code style guides)

-- Options on by default
-- vim.opt.termguicolors = true -- enable 24-bit colors
-- vim.opt.incsearch = true -- enable highlighting search in progress
-- vim.opt.autoindent = true -- copy indent from current line when starting new line
-- vim.opt.autoread = true -- auto update file if changed outside of nvim
