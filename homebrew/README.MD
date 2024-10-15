COMMAND TO RUN:

```SHELL
brew info --json=v2 --installed | jq '{
  formulae: [.formulae[] | select(.installed[]?.installed_on_request == true) | {name, tap, desc, homepage}],
  casks: [.casks[] | {name, tap, desc, homepage}]
}' > brew-user-installed.json
```

