return {
	settings = {
		java = {
			inlayHints = {
				parameterNames = {
					enabled = 'all', -- "none" | "literals" | "all"
					exclusions = { 'this' },
				},
				variableTypes = { enabled = true }, -- Variable type hints
				parameterTypes = { enabled = true }, -- Parameter type hints
			},
		},
	},
}
