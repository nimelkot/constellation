# Constellation

Constellation is a local-first terminal workspace for exploring concurrent agent threads as a dependency graph. It provides a persistent SQLite tree, a Textual dual-pane interface, and an MCP client boundary that keeps transport concerns separate from orchestration.

## Quick start

```console
python -m pip install -e .
constellation run "Investigate the flaky test" --interactive
constellation stars
constellation orbit --resume <node-id>
constellation orbit --from <parent-id> --title "Test hypothesis" --prompt "Run focused checks"
constellation status
constellation stop <node-id>
constellation delete <node-id> --yes
constellation api-key create --label "local development"
```

The default database is `.constellation/state.db`. Set `CONSTELLATION_DB` to use another location.

`forest` and `branch --resume` remain available as hidden compatibility aliases.

Use `orbit --from` to create a sub-mission under an existing node. The star map renders child missions with `├─` and `└─` connectors, plus `│` guides for deeper levels.

The selected node's detail panel shows its ID. In the UI, `s` stops and parks the selected mission, `d` deletes its entire sub-mission tree, and `Ctrl+P` opens the command palette. API keys are stored as hashes in `.constellation/api_keys.json`; the generated secret is printed only once.
